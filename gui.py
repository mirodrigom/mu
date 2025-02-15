from gamebot import GameBot
import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import os

class GameBotGUI:
    def __init__(self):
        self.bot = GameBot()  # Initialize the bot
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
        
        # Map selection dropdown
        self.map_var = tk.StringVar()
        self.map_selector = ttk.Combobox(self.root, textvariable=self.map_var)
        self.map_selector['values'] = ["noria", "lorencia", "tarkan", "dungeon3"]
        self.map_selector.current(0)  # Default to "noria"
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
        
        # Start periodic status updates
        self.update_status()
        
        # Start periodic log updates
        self.update_logs()
        
        # Start the GUI
        self.root.mainloop()
    
    def stop_bot(self):
        """Stop the bot and ensure it's not running."""
        self.bot.running = False
        self.status_label.config(text="Status: Bot stopped")
    
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
        threading.Thread(target=self.bot.run).start()
        self.status_label.config(text=f"Status: Bot manually exploring {selected_map}")
    
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
            print(f"Error updating status: {e}")
        
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

if __name__ == "__main__":
    gui = GameBotGUI()