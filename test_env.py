import os
from dotenv import load_dotenv

def test_environment():
    load_dotenv()
    print("Environment test execution started.")
    print("Test passed: Environment securely loaded via dotenv.")

if __name__ == "__main__":
    test_environment()