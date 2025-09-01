from posthog import Posthog
async def function_posthog_client_read(config_posthog_project_host,config_posthog_project_key):
   client_posthog=Posthog(config_posthog_project_key,host=config_posthog_project_host)
   return client_posthog
