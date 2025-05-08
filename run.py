import os
import sys

# Add the project root directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import and run the seeding script
from scripts.seed_data import seed_database

if __name__ == "__main__":
    seed_database() 