from openai import OpenAI
def function_openai_client_read(config_openai_key):
   client_openai=OpenAI(api_key=config_openai_key)
   return client_openai