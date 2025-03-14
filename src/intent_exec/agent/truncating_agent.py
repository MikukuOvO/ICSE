from autogen import UserProxyAgent

class TruncatingUserProxyAgent(UserProxyAgent):
    def run_code(self, *args, max_chars=100000, **kwargs):
        """
        Runs the code, then truncates the output to a maximum length.
        """
        result = super().run_code(*args, **kwargs)
        if len(result) > max_chars:
            return result[:max_chars] + "\n... [output truncated]"
        return result