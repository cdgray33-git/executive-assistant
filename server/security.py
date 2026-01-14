import os
def require_api_key(x_api_key: str):
    expected = os.environ.get("API_KEY")
    if not expected:
        cfg = os.path.expanduser("~/ExecutiveAssistant/config.env")
        if os.path.exists(cfg):
            with open(cfg) as f:
                for line in f:
                    if line.startswith("API_KEY"):
                        _, v = line.split("=",1); expected = v.strip().strip('"')
    if not expected or x_api_key != expected:
        raise PermissionError("Invalid API key")
