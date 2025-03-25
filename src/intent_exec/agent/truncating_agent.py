import tiktoken
from autogen import UserProxyAgent

class TruncatingUserProxyAgent(UserProxyAgent):
    def run_code(self, *args, max_tokens=10000, **kwargs):
        """
        Runs the code, then truncates the output to a maximum token length.
        Extracts the second element from result tuples for processing.
        """
        result = super().run_code(*args, **kwargs)

        # Check if result is a tuple with at least 2 elements
        if isinstance(result, tuple) and len(result) >= 2:
            # Extract the components
            exit_code = result[0]
            string_data = result[1]
            extra_data = result[2] if len(result) > 2 else None
            
            # Only tokenize the string part
            if isinstance(string_data, str):
                encoding = tiktoken.encoding_for_model("gpt-4-turbo")
                tokens = encoding.encode(string_data)
                
                if len(tokens) > max_tokens:
                    # Truncate only the string part
                    truncated_string = encoding.decode(tokens[:max_tokens]) + "\n... [output truncated]"
                    
                    # Return the tuple with the truncated string
                    if len(result) > 2:
                        return (exit_code, truncated_string, extra_data)
                    else:
                        return (exit_code, truncated_string)
            
            # Return the original result if no truncation needed
            return result
        
        # If result is a string (not a tuple), handle it directly
        elif isinstance(result, str):
            encoding = tiktoken.encoding_for_model("gpt-4-turbo")
            tokens = encoding.encode(result)
            
            if len(tokens) > max_tokens:
                return encoding.decode(tokens[:max_tokens]) + "\n... [output truncated]"
            
            return result
        
        # For any other type, return as is
        else:
            return result