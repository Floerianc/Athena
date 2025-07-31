import os
import math
import time
import sys
from threading import Thread
from colorama import Fore
import utils
from style import get_style

class ProgressBar:
    def __init__(
        self, 
        title: str,
        description: str = "",
        color: str = ""
    ) -> None:
        self.style = get_style(color)
        
        self.size = os.get_terminal_size()
        self.width = self.size.columns
        self.progress_width = self.width - 12
        
        self.completed = False
        self.last_progress = 0.0
        self.progress = 0.0
        
        self.update_time = 0.5
        self.step_time = 0.05
        
        self.title = title
        self.description = description
        self.lsep, self.rsep = "▏", "▕"
        self.fillChar = "█"
        self.space = " "
        
        self.thread = Thread(target=self.thread_loop)
        self.thread.start()
    
    def set_progress(self, new: float) -> None:
        if new > 1.0:
            self.completed = True
            new = 1.0
        self.progress = new
    
    def _time_to_steps(self) -> int:
        return math.floor(self.update_time / self.step_time)
    
    def _percentage_string(self, progress: float) -> str:
        return f"{round(progress*100):3d} %"
    
    def fill(self) -> None:
        last_fill_chars = math.floor(self.progress_width * self.last_progress)  # progress last time
        fill_chars = math.floor(self.progress_width * self.progress)            # progress now
        self.last_progress = self.progress                                      # update last progress
        steps = utils.rangespace(
            start=last_fill_chars, 
            stop=fill_chars, 
            steps=self._time_to_steps()
        )
        
        for step in steps:
            chars = round(step)  # amount of characters for progress bar
            filler = self.progress_width - chars  # amount of filler spaces
            percentage = step / self.progress_width
            
            sys.stdout.write(
                f"\r{self.lsep} "
                f"{self.style.accent_color}{self.fillChar*chars}{self.space*filler}{Fore.RESET}"
                f"{self.rsep} ({self._percentage_string(percentage)})")
            time.sleep(self.step_time)
            sys.stdout.flush()
    
    def render(self) -> None:
        print(self.style.main_color+self.title+Fore.RESET)
        print(self.description)
        self.fill()
    
    def thread_loop(self) -> None:
        self.render()
        while True:
            if self.last_progress != self.progress:
                self.fill()
            
            if self.progress >= 1.0:
                break
            time.sleep(self.update_time)


if __name__ == "__main__":
    p = ProgressBar(
        title="Loading Database content", 
        description="Loading your JSON file into the database and RAM to use it for the program.",
        color="black"
    )
    while not p.completed:
        time.sleep(1)
        p.set_progress(p.progress + 1)