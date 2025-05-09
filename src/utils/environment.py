import os
from dotenv import load_dotenv

def setup_environment():
    load_dotenv()


def _set_env(env_var: str):
    """Set environment variable if not already set."""
    if not os.getenv(env_var):
        os.environ[env_var] = input(f"Enter {env_var}: ")
    print(f"{env_var}: {'•' * 10}")  # Hide actual key values


def set_env_st(env_var: str, value: str):
    """Set environment variable with clearing."""
    if env_var in os.environ:
        del os.environ[env_var]
    os.environ[env_var] = value
    print(f"{env_var}: {value} {'•' * 10}")  # Hide actual key values