import yaml
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def load_config():
    with open('../context.yaml', 'r') as file:
        config = yaml.safe_load(file)
    
    # Set environment based on deployment context or default to 'nonprod'
    environment = os.getenv('ENVIRONMENT', 'nonprod')
    env_config = config['environments'][environment]

    # Replace placeholders with environment variables
    for key, value in env_config.items():
        if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
            env_var = value[2:-1]
            env_config[key] = os.getenv(env_var, '')

    return env_config