# models/base_loader.py
"""
Base model loader and API communication utilities.

This module provides functionality for loading and running large language models,
handling API communications, and task decomposition for complex problems.
"""

import json5 as json
import regex
import re
import subprocess
import pythonmonkey
from typing import Dict, Any, List, Tuple, Optional, Union
from vllm import LLM, SamplingParams
from openai import OpenAI

# jsonrepair = pythonmonkey.require('jsonrepair').jsonrepair

def escape_backslashes_in_json(json_str: str) -> str:
    """
    Escape backslashes and newlines in JSON string values.
    
    Args:
        json_str: The JSON string to process
        
    Returns:
        The processed JSON string with escaped special characters
    """
    def replacer(match):
        content = match.group(1)
        content = content.replace('\\', '\\\\')
        content = content.replace('\n', '\\n')
        return f'"{content}"'
    
    return re.sub(r'"([^"]*?)"', replacer, json_str, flags=re.DOTALL)


def call_api(prompt: str, 
             system_prompt: Optional[str] = None,
             client: Optional[OpenAI] = None,
             base_url: Optional[str] = None,
             model: str = "gpt-3.5-turbo", 
             api_key: Optional[str] = None, 
             max_tokens: Optional[int] = None, 
             temperature: float = 0.7,
             logprobs: bool = False,
             top_logprobs: int = 1,
             **kwargs) -> str:
    """
    Make API calls to OpenAI-compatible services.
    
    Args:
        prompt: The user prompt to send
        system_prompt: Optional system prompt to set context
        client: Pre-initialized OpenAI client
        base_url: Base URL for the API service
        model: Model name to use for generation
        api_key: API key for authentication
        max_tokens: Maximum tokens to generate
        temperature: Sampling temperature (0.0 to 2.0)
        logprobs: Whether to return log probabilities
        top_logprobs: Number of most likely tokens to return
        **kwargs: Additional parameters for the API call
        
    Returns:
        The generated response text
        
    Raises:
        AssertionError: If neither client nor api_key is provided
    """
    if not client:
        assert api_key is not None, 'Please input your api key'
        client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
    
    if not logprobs:
        top_logprobs = None

    messages = []
    if system_prompt is not None:
        messages.append({"role": "system", "content": system_prompt})
    if prompt:
        messages.append({"role": "user", "content": prompt}) 

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        logprobs=logprobs,
        top_logprobs=top_logprobs,
        **kwargs
    )
    return response.choices[0].message.content


class BaseModel:
    """
    Base model class for loading and running large language models.
    
    This class provides methods for model initialization, text generation,
    and task decomposition for complex mathematical and logical problems.
    """
    
    def __init__(self, model_path: str, system_prompt: str = "", device: Optional[str] = None):
        """
        Initialize the base model.
        
        Args:
            model_path: Path to the model files
            system_prompt: System prompt to set model behavior
            device: Device to run the model on (CPU/GPU)
        """
        self.device = device
        self.model_path = model_path
        self.llm = LLM(model=model_path)
        
        print("Running on ", device)
        self.system_prompt = system_prompt.strip() + "\n" if system_prompt else ""

    def generate(self, prompt: str, max_new_tokens: int = 512, 
                 temperature: float = 0.6, top_p: float = 0.9) -> str:
        """
        Generate text using the loaded model.
        
        Args:
            prompt: Input prompt for generation
            max_new_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature for randomness control
            top_p: Top-p sampling parameter for nucleus sampling
            
        Returns:
            Generated text response
        """
        sampling_params = SamplingParams(
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_new_tokens,
        )
        outputs = self.llm.generate(prompt, sampling_params)
        return outputs[0].outputs[0].text.strip()

    def generate_task_dag(self, task_background: str, task_question: str, 
                          user_input: str, requirement: str) -> Tuple[Dict[str, List[str]], bool]:
        """
        Generate a Directed Acyclic Graph (DAG) of subtasks for complex problems.
        
        This method decomposes a complex mathematical or logical problem into
        a sequence of computable sub-questions that can be solved step by step.
        
        Args:
            task_background: Background context for the problem
            task_question: The main question to be solved
            user_input: The complete user input containing the problem
            requirement: Additional requirements or constraints
            
        Returns:
            A tuple containing:
            - Dictionary mapping task IDs to [question, requirement] pairs
            - Boolean indicating success/failure of task decomposition
        """
        prompt = f"""
You are a problem decomposer, not a solver. Your task is to break down a complex math or logic problem into a sequence of strictly computable sub-questions. Each sub-question must represent a well-defined, executable step toward solving the original problem.

Each subtask must be phrased as a question. Do not solve the problem or output the final answer.

You MUST strictly output the result in the following **valid JSON** format:

Output:
{{
"original_question": "<repeat the original question>",
"subtasks": [
    "Q1: ...",
    "Q2: ...",
    ...
]
}}

⚠️ Important Rules:

- Do NOT include any final answer, intermediate answer, or numerical result.
- Do NOT perform or explain any computation.
- Do NOT include any text outside the JSON object.
- Each subtask must be directly computable (e.g., calculate a value, rewrite an expression, identify a condition).
- Use clear and concise language appropriate for step-by-step problem solving.

Here are some examples:

Example 1:
Input:
One root of the equation $5x^2+kx=4$ is 2. What is the other?

Output:
{{
  "original_question": "One root of the equation $5x^2+kx=4$ is 2. What is the other?",
  "subtasks": [
    "Q1: What is the equation rewritten in standard quadratic form?",
    "Q2: What is the product of the roots of this quadratic equation?",
    "Q3: Given one root is 2, what is the other root?"
  ]
}}

Example 2:
Input:
A box contains 3 red and 5 blue balls. Two balls are drawn without replacement. What is the probability that both are red?

Output:
{{
  "original_question": "A box contains 3 red and 5 blue balls. Two balls are drawn without replacement. What is the probability that both are red?",
  "subtasks": [
    "Q1: How many total balls are in the box?",
    "Q2: What is the probability that the first ball drawn is red?",
    "Q3: What is the probability that the second ball drawn is red given that the first was red?",
    "Q4: What is the product of the two probabilities?"
  ]
}}

Do NOT include any explanation, prefix, or suffix before or after the JSON. Output ONLY the JSON object.

Now decompose the following problem:

Input:
{user_input}

Output:"""
        
        result = self.generate(prompt, max_new_tokens=512, temperature=0.6)
        print(f"Raw result: {result}")
        print(f"[DEBUG] repr: {repr(result)}")

        try:
            cleaned = result.strip().lstrip('\ufeff')
            dag_dict = json.loads(cleaned)
            steps = {}
            for index, s in enumerate(dag_dict.get("subtasks", [])):
                steps[str(index + 1)] = [s, requirement]

            for subtask_id in steps:
                print(steps[subtask_id])

            return steps, True
            
        except ValueError as e:
            print(f"[WARN] Direct JSON decode failed: {e}")
            try:
                match = re.search(
                    r'\{\s*"original_question"\s*:\s*".+?",\s*"subtasks"\s*:\s*\[[\s\S]+?\]\s*\}',
                    result,
                    flags=re.DOTALL
                )
                if match:
                    json_str = match.group(0)
                    print(f"[DEBUG] Extracted JSON: {json_str}")

                    jsonrepair = subprocess.run(["node", "repair.js"],input=result.encode("utf-8"),stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                    fixed_json_str = jsonrepair.stdout.decode("utf-8")

                    # fixed_json_str = jsonrepair(json_str)
                    print(f"[DEBUG] Escaped JSON: {fixed_json_str}")
                    dag_dict = json.loads(fixed_json_str)
                    steps = {}
                    for index, s in enumerate(dag_dict.get("subtasks", [])):
                        steps[str(index + 1)] = [s, requirement]

                    for subtask_id in steps:
                        print(steps[subtask_id])

                    return steps, True
                else:
                    print("[ERROR] JSON not found in output.")
                    return {}, False
            except Exception as e:
                print(f"[ERROR] Failed to extract or repair JSON: {e}")
                return {}, False
        except Exception as e:
            print(f"[ERROR] Unexpected error: {e}")
            return {}, False

    def extract_task(self, user_input: str) -> Tuple[str, str, bool]:
        """
        Extract background information and question from a problem statement.
        
        This method separates the background context from the actual question
        in mathematical problem statements to facilitate better task decomposition.
        
        Args:
            user_input: The complete problem statement
            
        Returns:
            A tuple containing:
            - Background context string
            - Question string
            - Boolean indicating success/failure of extraction
        """
        prompt = """You are a text extractor. Your task is ONLY to separate the background information from the question in math problem statements.

Each input contains:
- Background: context, assumptions, formulas, constraints, and setup.
- Question: the final sentence or phrase that asks what needs to be found, calculated, or determined.

⚠️ IMPORTANT RULES:
- DO NOT solve or explain anything.
- DO NOT rewrite or infer any missing values.
- DO NOT modify, simplify, or expand any math expressions.
- DO NOT perform any calculations.
- DO NOT guess or assume anything.
- Only CUT the question part from the background and return both.

If the question comes after a comma, move everything after that comma to the "question".

Return your output in the following strict JSON format:
{{
  "background": "<only the setup or context>",
  "question": "<only the question sentence>"
}}

---

Example:

Input:
The perimeter of a rectangle is 24 inches. What is the number of square inches in the maximum possible area for this rectangle?

Output:
{{
  "background": "The perimeter of a rectangle is 24 inches.",
  "question": "What is the number of square inches in the maximum possible area for this rectangle?"
}}

---

Input:
If $A=2+i$, $O=-4$, $P=-i$, and $S=2+4i$, find $A-O+P+S$.

Output:
{{
  "background": "If $A=2+i$, $O=-4$, $P=-i$, and $S=2+4i$.",
  "question": "Find $A-O+P+S$"
}}

---

Now extract background and question from the following input.
Remember: do NOT solve the problem. Only extract.

Input:
{user_input}

Output:""".format(user_input=user_input.strip())
        
        result = self.generate(prompt, temperature=0.6, max_new_tokens=512)
        print(f"Raw Result: {result}")
        print(f"[DEBUG] repr: {repr(result)}")

        # Try direct JSON parsing
        try:
            cleaned = result.strip().lstrip('\ufeff')
            data = json.loads(cleaned)
            return data["background"], data["question"], True
        except ValueError as e:
            print(f"[WARN] Direct JSON decode failed: {e}")
            try:
                # Stronger regex matching for complete multi-line JSON
                match = re.search(
                    r'\{\s*"background"\s*:\s*"[\s\S]+?",\s*"question"\s*:\s*"[\s\S]+?"\s*\}', 
                    result
                )
                if match:
                    json_str = match.group(0)
                    print(f"[DEBUG] Extracted JSON: {json_str}")

                    jsonrepair = subprocess.run(["node", "repair.js"],input=result.encode("utf-8"),stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                    fixed_json_str = jsonrepair.stdout.decode("utf-8")

                    # fixed_json_str = jsonrepair(json_str)
                    print(f"[DEBUG] Escaped JSON: {fixed_json_str}")

                    data = json.loads(fixed_json_str)
                    return data["background"], data["question"], True
                else:
                    print("[ERROR] JSON not found in output.")
                    return "", "", False
            except Exception as e:
                print(f"[ERROR] Failed to extract or repair JSON: {e}")
                return "", "", False
        except Exception as e:
            print(f"[ERROR] Unexpected error: {e}")
            return "", "", False