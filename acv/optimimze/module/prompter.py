import os
import yaml
import importlib
from pathlib import Path
from jinja2 import Template
from autogen.coding import LocalCommandLineCodeExecutor
from .utils import load_yaml, get_ancestor_path

base_path = get_ancestor_path(2)

class Prompter:
    def __init__(self, prompt_template: str = ""):
        self.prompt_template = prompt_template
        self._system_message = ""
        self._user_content = ""
        self._function_descptions = ""
        self._promql_descriptions = ""
        self._service_slo_descriptions = ""

    @property
    def system_message(self):
        return (
            self._system_message
            + "\n"
            + self._service_slo_descriptions
            + "\n"
            + self._function_descptions
            + "\n"
            + self._promql_descriptions
        )

    @property
    def critic_message(self):
        return self._critic_message

    @property
    def user_content(self):
        return self._user_content

    def load_prompt_template(self, prompt_file: str):
        if os.path.exists(prompt_file):
            self.prompt = load_yaml(prompt_file)
            if "system" in self.prompt:
                self._system_message = self.prompt["system"]
            if "critic" in self.prompt:
                self._critic_message = self.prompt["critic"]
            if "user" in self.prompt:
                self._user_content = self.prompt["user"]
        else:
            raise FileNotFoundError(f"Prompt template not found at {prompt_file}")

    def fill_system_message(self, placeholders: dict):
        template = Template(self.prompt["system"])
        self._system_message = template.render(**placeholders)

    def fill_critic_message(self, placeholders: dict):
        template = Template(self.prompt["critic"])
        self._critic_message = template.render(**placeholders)

    def fill_user_content(self, placeholders: dict):
        template = Template(self.prompt["user"])
        self._user_content = template.render(**placeholders)

    def generate_service_slos(self, deployment_name: str, slo_path: str):
        import yaml

        # Load the SLO YAML file
        with open(slo_path, "r", encoding="utf-8") as f:
            slo_data = yaml.safe_load(f)

        # Extract data under 'social-network' and filter entries matching the deployment_name
        network_data = slo_data.get("social-network", {})
        filtered_data = {}
        for slo_key, slo_info in network_data.items():
            if isinstance(slo_info, dict) and slo_info.get("deploymentName") == deployment_name:
                filtered_data[slo_key] = slo_info

        # If we found matches, generate a prompt template; otherwise, note no matches
        if filtered_data:
            slo_str = yaml.dump(filtered_data, sort_keys=False)
            prompt_template = f"""
            # Healthy State Judgement
            
            To determine whether the service is anomaly, you should judge based on following rules:
            - A service is considered an anomaly if it is part of a sequence of at least one consecutive anomalous points or if its latency continues to plummet or surge abruptly.
            - A service is considered an anomaly if it is identified as a continuous high latency anomaly, remaining above a normal level for a prolonged duration, thereby deviating from the anticipated norm.
            - Normal service latency may exhibit variability, which should not be confused with anomalies.
            """
        else:
            prompt_template = (
                f"No SLO data found for the deployment '{deployment_name}'."
            )

        # Store or return the generated description
        self._service_slo_descriptions = prompt_template


    def generate_function_descriptions(self, tool_functions_path: str):
        def load_module(module_path: str):
            spec = importlib.util.spec_from_file_location("module_name", module_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module

        def convert_path_to_module(module_path: Path):
            module_path = ".".join(module_path.with_suffix("").parts)
            return module_path

        module = load_module(tool_functions_path)
        functions = module.__dict__["functions"]
        model_name = convert_path_to_module(Path(tool_functions_path)).removeprefix("src.")
        executor = LocalCommandLineCodeExecutor(work_dir=base_path, functions=functions)
        prompt_template = f"""
        \n# Introduction for Tool Functions
        - You have access to the following tool functions.
        They can be accessed from the module called `{model_name}` by their function names.
        - For example, if there was a function called `foo` you could import it by writing `from {model_name} import foo`
        $functions
        """
        self._function_descptions = executor.format_functions_for_prompt(
            prompt_template=prompt_template
        )

    def generate_promQL(self, deployment_name, promQL_path: str):
        # Load the PromQL YAML file
        with open(promQL_path, "r", encoding="utf-8") as f:
            promql_data = yaml.safe_load(f)

        # Extract only entries matching the given deployment_name
        network_data = promql_data.get("social-network", {})
        filtered_data = {}
        for metric_key, metric_info in network_data.items():
            # Ensure metric_info is a dict and has a matching deploymentName
            if isinstance(metric_info, dict) and metric_info.get("deploymentName") == deployment_name:
                filtered_data[metric_key] = metric_info

        # Convert the filtered data to YAML; if no matches, this will be empty
        promql_str = yaml.dump(filtered_data, sort_keys=False)

        # Create a prompt template that describes the PromQL mappings
        prompt_template = f"""
        # PromQL Queries Mapping
        The following YAML content defines Prometheus queries mapped to service metrics.
        These entries match the deployment name '{deployment_name}':

        {promql_str}
        """
        self._promql_descriptions = prompt_template

