import subprocess, os
OLLAMA_CLI = os.environ.get("OLLAMA_BIN", "ollama")
class OllamaAdapter:
    def ping(self):
        try:
            subprocess.run([OLLAMA_CLI, "list"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            return True
        except Exception:
            return False
