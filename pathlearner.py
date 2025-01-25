import json
import time
import logging
from typing import List, Dict, Tuple, Optional
import numpy as np

class PathLearner:
    def __init__(self):
        self.paths_file = 'path_history.json'
        self.failed_paths_file = 'failed_paths.json'
        self.good_paths_file = 'good_path.json'  # Add this line
        self.load_history()
        self.current_path = []
        self.obstacles = set()
        self.start_time = None

    def load_history(self):
        try:
            with open(self.paths_file, 'r') as f:
                self.history = json.load(f)
            with open(self.failed_paths_file, 'r') as f:
                self.failed_paths = json.load(f)
            with open(self.good_paths_file, 'r') as f:  # Add this block
                self.good_paths = json.load(f)
        except:
            self.history = {'paths': [], 'obstacles': []}
            self.failed_paths = {'paths': []}
            self.good_paths = {'paths': []}  # Add this line

    def save_history(self):
        with open(self.paths_file, 'w') as f:
            json.dump(self.history, f)

    def record_move(self, x: int, y: int, success: bool = True):
        self.current_path.append({
            'x': x, 
            'y': y,
            'timestamp': time.time()
        })
        if not success:
            self.obstacles.add((x, y))
    
    def record_good_path(self, game_bot, map_name, duration=10, interval=1):
        print(f"Recording a good path for {map_name} for {duration} seconds at {interval} second intervals.")
        good_path = []
        start_time = time.time()
        
        while time.time() - start_time < duration:
            current_pos = game_bot.get_current_position()
            if current_pos:
                good_path.append({'x': game_bot.current_x, 'y': game_bot.current_y, 'timestamp': time.time()})
            
            time.sleep(interval)

        self._save_good_path(good_path, map_name)

    def _save_good_path(self, good_path, map_name):
        if good_path:
            self.good_paths.setdefault(map_name, []).append({'points': good_path, 'timestamp': time.time()})
            with open(f"{map_name}.json", 'w') as f:
                json.dump(self.good_paths[map_name], f)
            print(f"Good path for {map_name} saved.")
        else:
            print(f"No points recorded for {map_name}. Path not saved.")

    def save_path(self, success: bool = True):
        if self.current_path:
            self.history['paths'].append({
                'points': self.current_path,
                'success': success,
                'timestamp': time.time()
            })
            if success:
                self.good_paths['paths'].append({
                    'points': self.current_path,
                    'timestamp': time.time()
                })
                with open(self.good_paths_file, 'w') as f:
                    json.dump(self.good_paths, f)
            self.current_path = []
            self.save_history()

    def save_failed_path(self, start_pos: Tuple[int, int], target_pos: Tuple[int, int]):
        failed_path = {
            'start': start_pos,
            'target': target_pos,
            'timestamp': time.time(),
            'path_taken': self.current_path
        }
        self.failed_paths['paths'].append(failed_path)
        with open(self.failed_paths_file, 'w') as f:
            json.dump(self.failed_paths, f)

    def should_skip_path(self, start_pos: Tuple[int, int], target_pos: Tuple[int, int]) -> bool:
        for path in self.failed_paths['paths']:
            if (path['start'] == start_pos and 
                path['target'] == target_pos and 
                time.time() - path['timestamp'] < 3600):  # Skip for 1 hour
                return True
        return False

    def get_best_path(self, current_pos: Tuple[int, int], target_pos: Tuple[int, int]) -> Optional[List[Dict[str, int]]]:
        successful_paths = [p for p in self.history['paths'] 
                            if p['success'] and time.time() - p['timestamp'] < 86400]  # Only use paths from last 24h
        
        if not successful_paths:
            return None
        
        best_path = None
        best_score = float('inf')
        
        for path in successful_paths:
            start = (path['points'][0]['x'], path['points'][0]['y'])
            end = (path['points'][-1]['x'], path['points'][-1]['y'])
            
            # Calculate distances
            start_dist = self.calculate_distance(start, current_pos)
            end_dist = self.calculate_distance(end, target_pos)
            
            # Calculate path efficiency
            path_length = len(path['points'])
            direct_distance = self.calculate_distance(start, end)
            efficiency = direct_distance / path_length if path_length > 0 else 0
            
            # Calculate score (lower is better)
            score = (start_dist + end_dist) / (efficiency + 0.1)
            
            if score < best_score:
                best_score = score
                best_path = path['points']
                
        return best_path

    def calculate_distance(self, pos1: Tuple[int, int], pos2: Tuple[int, int]) -> float:
        return ((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)**0.5

    def clean_old_paths(self, max_age_hours: int = 24):
        current_time = time.time()
        
        # Clean successful paths
        self.history['paths'] = [
            p for p in self.history['paths'] 
            if current_time - p['timestamp'] < max_age_hours * 3600
        ]
        
        # Clean failed paths
        self.failed_paths['paths'] = [
            p for p in self.failed_paths['paths']
            if current_time - p['timestamp'] < max_age_hours * 3600
        ]
        
        self.save_history()
        with open(self.failed_paths_file, 'w') as f:
            json.dump(self.failed_paths, f)