import tkinter as tk
import threading
import os
import logging

from tkinter import ttk, scrolledtext
from interface import Interface
from config import Configuration
from gameclass import GameClass
from memory import Memory
from movement import Movement
from gamebot import GameBot
from logger_config import setup_logging


class GameBotGUI:
    def __init__(self):
        setup_logging()
        self.logging = logging.getLogger(__name__)
        self.root = tk.Tk()
        self.root.title("Avespalov Control")
        
        # Set window to always be on top
        self.root.attributes('-topmost', True)
        
        # Set window transparency (0.0 = fully transparent, 1.0 = fully opaque)
        self.root.attributes('-alpha', 0.9)  # Slightly transparent
        
        # Set window position to bottom-left corner of the screen
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        window_width = 400  # Adjust as needed
        window_height = 600  # Adjust as needed
        self.root.geometry(f"{window_width}x{window_height}+0+{screen_height - window_height}")
        
        # Status label for bot actions
        self.status_label = ttk.Label(self.root, text="Status: Bot is idle", font=("Arial", 10))
        self.status_label.pack(pady=10)
        
        # Create buttons with slight transparency
        button_style = ttk.Style()
        button_style.configure('TButton', background='#ffffff', foreground='black')  # Adjust colors as needed
        
        self.start_button = ttk.Button(self.root, text="Start Bot (F1)", command=self.start_bot, style='TButton')
        self.start_button.pack(pady=10)
        
        self.manual_explore_button = ttk.Button(self.root, text="Manually Explore (F2)", command=self.manual_explore, style='TButton')
        self.manual_explore_button.pack(pady=10)
        
        self.auto_explore_button = ttk.Button(self.root, text="Automatically Explore (F3)", command=self.auto_explore, style='TButton')
        self.auto_explore_button.pack(pady=10)
        
        self.stop_button = ttk.Button(self.root, text="Stop Bot (F9)", command=self.stop_bot, style='TButton')
        self.stop_button.pack(pady=10)
        
        # Add a new button for saving and stopping manual exploration
        self.save_stop_button = ttk.Button(self.root, text="Save & Stop Manual Exploration", command=self.save_and_stop_manual, style='TButton')
        self.save_stop_button.pack(pady=10)
        self.save_stop_button.config(state=tk.DISABLED)  # Initially disabled
        
        # Map selection dropdown
        self.map_var = tk.StringVar()
        self.map_selector = ttk.Combobox(self.root, textvariable=self.map_var)
        self.map_selector['values'] = ["noria", "lorencia", "tarkan", "dungeon3", "losttower", "losttower5", "losttower7", "kanturu", "vulcanus"]
        self.map_selector.current(0)
        self.map_selector.pack(pady=10)
        
        # Status display
        self.status_frame = ttk.LabelFrame(self.root, text="Current Status")
        self.status_frame.pack(pady=10, padx=10, fill="x")
        
        self.status_labels = {}
        fields = [
            "current_reset", "current_level", "current_map", "current_strenght",
            "current_agility", "current_vitality", "current_energy", "current_command",
            "available_points", "mulheper_active", "current_location"
        ]
        
        for field in fields:
            label = ttk.Label(self.status_frame, text=f"{field.replace('_', ' ').title()}: N/A")
            label.pack(anchor="w")
            self.status_labels[field] = label
        
        # Log display
        self.log_frame = ttk.LabelFrame(self.root, text="Logs")
        self.log_frame.pack(pady=10, padx=10, fill="both", expand=True)
        
        self.log_text = scrolledtext.ScrolledText(self.log_frame, wrap=tk.WORD, bg="white", fg="black")
        self.log_text.pack(fill="both", expand=True)
        
        # Bind keys
        self.root.bind('<F1>', lambda event: self.start_bot())
        self.root.bind('<F2>', lambda event: self.manual_explore())
        self.root.bind('<F3>', lambda event: self.auto_explore())
        self.root.bind('<F9>', lambda event: self.stop_bot())
        self.root.bind('<Escape>', lambda event: self.toggle_gui_visibility())  # Hide/show GUI with Escape key
        
        # Threads and events
        self.stop_event = threading.Event()

        # Initialize bot components
        config = Configuration()
        interface = Interface(config)
        gameclass = GameClass()
        memory = Memory(config)
        movement = Movement(interface=interface, config=config, memory=memory)
        self.bot = GameBot(
            config=config,
            interface=interface,
            gameclass=gameclass,
            memory=memory,
            movement=movement,
            stop_event=self.stop_event,
            root=self.root  # Pass the root reference to GameBot
        )

        # Start periodic status updates
        self.update_status()
        
        # Start periodic log updates
        self.update_logs()
        
        # Start the GUI
        self.root.mainloop()
    
    def disable_buttons(self):
        """Disable all buttons except the save & stop button."""
        self.start_button.config(state=tk.DISABLED)
        self.manual_explore_button.config(state=tk.DISABLED)
        self.auto_explore_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.DISABLED)
        self.save_stop_button.config(state=tk.NORMAL)

    def enable_buttons(self):
        """Enable all buttons and disable the save & stop button."""
        self.start_button.config(state=tk.NORMAL)
        self.manual_explore_button.config(state=tk.NORMAL)
        self.auto_explore_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.NORMAL)
        self.save_stop_button.config(state=tk.DISABLED)

    
    def start_bot(self):
        """Start the bot in normal mode."""
        self.stop_bot()  # Stop the bot before starting a new action
        self.bot.EXPLORE_MAP = ""
        self.bot.EXPLORE_MODE = False
        self.bot.EXPLORE_MANUAL_MODE = False
        self.bot.SKIP_ATTRIBUTES = False
        self.bot.running = True
        threading.Thread(target=self.bot.run).start()
        self.status_label.config(text="Status: Bot started in normal mode")
    
    def manual_explore(self):
        """Start the bot in manual exploration mode."""
        self.stop_bot()  # Stop the bot before starting a new action
        selected_map = self.map_var.get()
        self.bot.EXPLORE_MAP = selected_map
        self.bot.EXPLORE_MODE = True
        self.bot.EXPLORE_MANUAL_MODE = True
        self.bot.SKIP_ATTRIBUTES = False
        self.bot.running = True
        threading.Thread(target=self.bot.run).start()
        self.status_label.config(text=f"Status: Bot manually exploring {selected_map}")
        self.disable_buttons()  # Disable all buttons except save & stop
        self.save_stop_button.config(state=tk.NORMAL)  # Enable the save & stop button
    
    def auto_explore(self):
        """Start the bot in automatic exploration mode."""
        self.stop_bot()  # Stop the bot before starting a new action
        selected_map = self.map_var.get()
        self.bot.EXPLORE_MAP = selected_map
        self.bot.EXPLORE_MODE = True
        self.bot.EXPLORE_MANUAL_MODE = False
        self.bot.SKIP_ATTRIBUTES = False
        threading.Thread(target=self.bot.run).start()
        self.status_label.config(text=f"Status: Bot auto exploring {selected_map}")
    
    def update_status(self):
        """Update the status display every 5 seconds."""
        try:
            # Fetch the current game state
            game_state = self.bot.config.get_game_state()
            
            # Update the labels with the relevant fields
            for field, label in self.status_labels.items():
                value = game_state.get(field, "N/A")
                if field == "current_location" and isinstance(value, list):
                    value = f"[{value[0]}, {value[1]}]"
                label.config(text=f"{field.replace('_', ' ').title()}: {value}")
        except Exception as e:
            self.logging.error(f"Error updating status: {e}")
        
        # Schedule the next update
        self.root.after(5000, self.update_status)
    
    def toggle_gui_visibility(self):
        """Toggle the visibility of the GUI window."""
        if self.root.state() == "normal":
            self.root.withdraw()  # Hide the window
        else:
            self.root.deiconify()  # Show the window
    
    def update_logs(self):
        """Update the log display with the latest content from logs/game.log."""
        log_file = "logs/game.log"
        if os.path.exists(log_file):
            with open(log_file, "r") as file:
                logs = file.read()
            self.log_text.delete(1.0, tk.END)  # Clear the current content
            self.log_text.insert(tk.END, logs)  # Insert the latest logs
            self.log_text.yview(tk.END)  # Scroll to the bottom
        
        # Schedule the next update
        self.root.after(1000, self.update_logs)

    def save_and_stop_manual(self):
        """Save the manual exploration data and stop the process."""
        self.logging.info("Save & Stop Manual Exploration button clicked.")
        
        def cleanup():
            try:
                # Disable buttons during cleanup
                self.save_stop_button.config(state=tk.DISABLED)
                
                # Stop all bot operations
                self.bot.running = False
                self.bot.stop_event.set()
                
                # Save and cleanup exploration data
                if hasattr(self.bot, 'save_manual_exploration_data'):
                    self.logging.info("Calling save_manual_exploration_data on bot.")
                    self.bot.save_manual_exploration_data()
                
                self.enable_buttons()
                self.status_label.config(text="Status: Manual exploration saved and stopped")
            except Exception as e:
                self.logging.error(f"Error during cleanup: {e}")
                self.enable_buttons()
            finally:
                # Ensure bot is fully stopped
                if hasattr(self.bot, 'stop_event'):
                    self.bot.stop_event.set()
                if hasattr(self.bot, 'grid'):
                    self.bot.grid = None
        
        # Schedule cleanup in the main thread
        self.root.after_idle(cleanup)

    def stop_bot(self):
        """Stop the bot and ensure it's not running."""
        self.bot.running = False
        self.bot.manual_explore_running = False  # Add this line
        self.stop_event.set()
        self.status_label.config(text="Status: Bot stopped")
        self.enable_buttons()
        self.logging.info("Stopped")
        
        # Clean up the grid window if it exists
        if hasattr(self.bot, 'grid') and self.bot.grid:
            self.root.after(0, self.bot.destroy_grid_safely)

    def destroy_grid_safely(self):
        """Thread-safe grid window destruction."""
        if hasattr(self.bot, 'grid') and self.bot.grid:
            self.bot.destroy_grid_safely()

if __name__ == "__main__":
    gui = GameBotGUI()