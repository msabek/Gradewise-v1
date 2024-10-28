from typing import Dict, Callable, Optional, Any, List, Union
import ollama
from ollama._types import Message
import json
import re
import time
import logging
import openai
import anthropic
import os
import requests
from .config import Config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GradingSystem:
    def __init__(self):
        """Initialize the grading system with API clients"""
        self.local_models = []
        self.online_models = {}
        self.openai_client = None
        self.claude_client = None
        self.groq_api_key = None
        self._init_api_clients()
        self.refresh_available_models()

    def _validate_api_key(self, api_key: str, provider: str) -> bool:
        """Validate API key for a specific provider"""
        try:
            if provider.lower() == "groq":
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                response = requests.get(
                    "https://api.groq.com/openai/v1/models",
                    headers=headers,
                    timeout=10
                )
                return response.ok
            elif provider.lower() == "anthropic":
                headers = {"x-api-key": api_key}
                response = requests.get(
                    "https://api.anthropic.com/v1/models",
                    headers=headers,
                    timeout=10
                )
                return response.ok
            elif provider.lower() == "openai":
                client = openai.Client(api_key=api_key)
                response = client.models.list()
                return True
            return False
        except Exception as e:
            logger.error(f"Error validating {provider} API key: {str(e)}")
            return False

    def _init_api_clients(self):
        """Initialize API clients with validation"""
        # OpenAI setup
        openai_key = os.environ.get('OPENAI_API_KEY')
        if openai_key and self._validate_api_key(openai_key, "openai"):
            try:
                self.openai_client = openai.Client(api_key=openai_key)
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {str(e)}")
                self.openai_client = None

        # Anthropic setup
        anthropic_key = os.environ.get('ANTHROPIC_API_KEY')
        if anthropic_key and self._validate_api_key(anthropic_key, "anthropic"):
            try:
                self.claude_client = anthropic.Client(api_key=anthropic_key)
            except Exception as e:
                logger.error(f"Failed to initialize Claude client: {str(e)}")
                self.claude_client = None

        # Groq setup
        groq_key = os.environ.get('GROQ_API_KEY')
        if groq_key and self._validate_api_key(groq_key, "groq"):
            self.groq_api_key = groq_key
        else:
            self.groq_api_key = None

    def get_available_models(self, provider: str) -> List[str]:
        """Get available models for a specific provider"""
        try:
            if provider == "Local Only":
                try:
                    response = requests.get("http://localhost:11434/api/tags", timeout=5)
                    if response.ok:
                        return [model["name"] for model in response.json().get("models", [])]
                    logger.warning("Local models not available")
                except requests.exceptions.RequestException as e:
                    logger.warning(f"Could not connect to local Ollama server: {str(e)}")
                return []
            else:
                provider_key = provider.lower()
                if provider_key in self.online_models:
                    return self.online_models[provider_key]
            return []
        except Exception as e:
            logger.error(f"Error fetching models: {str(e)}")
            return []

    def _get_provider_from_model(self, model: str) -> str:
        """Determine the provider based on model name"""
        if model in self.local_models:
            return "local"
        for provider, models in self.online_models.items():
            if model in models:
                return provider
        return "local"  # Default to local if unknown

    def refresh_available_models(self):
        """Refresh available models from all providers"""
        try:
            # Get local models from Ollama
            try:
                response = requests.get("http://localhost:11434/api/tags", timeout=5)
                if response.ok:
                    self.local_models = [model["name"] for model in response.json().get("models", [])]
                else:
                    logger.warning("Local models not available")
            except requests.exceptions.RequestException as e:
                logger.warning(f"Could not connect to local Ollama server: {str(e)}")
                self.local_models = []

            # Get OpenAI models
            if self.openai_client:
                response = self.openai_client.models.list()
                self.online_models['openai'] = [
                    model.id for model in response.data 
                    if model.id.startswith(('gpt-3', 'gpt-4'))
                ]

            # Get Claude models
            if self.claude_client:
                headers = {"x-api-key": os.environ['ANTHROPIC_API_KEY']}
                response = requests.get(
                    "https://api.anthropic.com/v1/models",
                    headers=headers,
                    timeout=10
                )
                if response.ok:
                    self.online_models['claude'] = [
                        model['id'] for model in response.json().get('models', [])
                    ]

            # Get Groq models
            if self.groq_api_key:
                headers = {
                    "Authorization": f"Bearer {self.groq_api_key}",
                    "Content-Type": "application/json"
                }
                response = requests.get(
                    "https://api.groq.com/openai/v1/models",
                    headers=headers,
                    timeout=10
                )
                if response.ok:
                    self.online_models['groq'] = [
                        model['id'] for model in response.json().get('data', [])
                        if model.get('active', True)
                    ]

        except Exception as e:
            logger.error(f"Error refreshing models: {str(e)}")
            self.local_models = []
            self.online_models = {}

    def _sanitize_json_text(self, text: str) -> str:
        """Clean and prepare text for JSON parsing"""
        # Remove code block markers
        text = re.sub(r'```(?:json)?\n?(.*?)```', r'\1', text, flags=re.DOTALL)
        # Remove comments
        text = re.sub(r'//.*?\n|/\*.*?\*/', '', text, flags=re.DOTALL)
        # Remove leading/trailing whitespace
        text = text.strip()
        return text

    def _extract_json_object(self, text: str) -> Optional[str]:
        """Extract valid JSON object from text"""
        patterns = [
            r'\{(?:[^{}]|(?R))*\}',  # Match nested JSON objects
            r'\{[^}]+\}',            # Match simple JSON objects
            r'\{.*?\}(?=\s|$)'       # Match JSON objects with boundaries
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.DOTALL)
            for match in matches:
                try:
                    json_str = match.group(0)
                    json.loads(json_str)  # Validate JSON
                    return json_str
                except json.JSONDecodeError:
                    continue
        return None

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Enhanced JSON response parsing with robust error handling"""
        try:
            # Clean and prepare text
            cleaned_text = self._sanitize_json_text(response)
            
            # Try direct JSON parsing
            try:
                return json.loads(cleaned_text)
            except json.JSONDecodeError:
                # Try to extract JSON object
                json_str = self._extract_json_object(cleaned_text)
                if json_str:
                    return json.loads(json_str)
                
                # Fallback to structured extraction
                extracted = {
                    "score": 0,
                    "feedback": "",
                    "improvements": [],
                    "breakdown": {},
                    "raw_llm_output": response
                }
                
                # Extract score
                score_patterns = [
                    r'(?:score|grade|marks?)[:\s]+(\d+(?:\.\d+)?)',
                    r'(\d+(?:\.\d+)?)\s*(?:/|\s*out\s*of\s*)(?:20|twenty)',
                ]
                for pattern in score_patterns:
                    match = re.search(pattern, cleaned_text, re.IGNORECASE)
                    if match:
                        extracted["score"] = min(float(match.group(1)), 20)
                        break
                
                # Extract feedback
                feedback_match = re.search(
                    r'(?:feedback|comments?)[:\s]+([^\n]+)',
                    cleaned_text,
                    re.IGNORECASE
                )
                if feedback_match:
                    extracted["feedback"] = feedback_match.group(1).strip()
                
                # Extract improvements
                improvements_section = re.search(
                    r'(?:improvements?|suggestions?)[:\s]+((?:[^\n]+\n?)+)',
                    cleaned_text,
                    re.IGNORECASE
                )
                if improvements_section:
                    improvements = re.split(
                        r'(?:\d+\.|•|-|\n)+',
                        improvements_section.group(1)
                    )
                    extracted["improvements"] = [
                        imp.strip() for imp in improvements if imp.strip()
                    ]
                
                # Extract breakdown
                breakdown_matches = re.findall(
                    r'(?:question|part|section)\s*(\d+)[:\s]+(\d+(?:\.\d+)?)',
                    cleaned_text,
                    re.IGNORECASE
                )
                if breakdown_matches:
                    extracted["breakdown"] = {
                        f"question{q}": float(s) for q, s in breakdown_matches
                    }
                
                return extracted

        except Exception as e:
            logger.error(f"Error parsing response: {str(e)}")
            return {
                "score": 0,
                "feedback": "Error parsing model response",
                "improvements": ["Unable to parse model response"],
                "breakdown": {"error": str(e)},
                "raw_llm_output": response
            }

    def evaluate_submission(
        self,
        student_solution: str,
        ideal_solution: str,
        grading_instructions: str,
        model: str = "llama2:3.2",
        update_callback: Optional[Callable] = None,
        api_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Evaluate a student submission using specified model"""
        try:
            # Initialize temporary client with provided API key
            if api_key:
                provider = self._get_provider_from_model(model)
                if self._validate_api_key(api_key, provider):
                    if provider == "groq":
                        self.groq_api_key = api_key
                    elif provider == "anthropic":
                        self.claude_client = anthropic.Client(api_key=api_key)
                    elif provider == "openai":
                        self.openai_client = openai.Client(api_key=api_key)
                else:
                    raise ValueError(f"Invalid API key for {provider}")

            json_format_prompts = {
                "openai": "\nRespond with a valid JSON object only, no additional text.",
                "claude": "\nProvide response as a JSON object, no other text.",
                "groq": "\nOutput only a valid JSON object, nothing else.",
                "local": "\nFormat response as valid JSON."
            }

            prompt = f'''Grade this student solution following these instructions:

GRADING INSTRUCTIONS:
{grading_instructions}

IDEAL SOLUTION:
{ideal_solution}

STUDENT SOLUTION:
{student_solution}

Respond with a JSON object containing:
{{
    "score": <number between 0-20>,
    "feedback": "<detailed feedback>",
    "improvements": ["<specific improvement suggestions>"],
    "breakdown": {{
        "question1": <score>,
        "question2": <score>,
        ...
    }}
}}

{json_format_prompts.get(self._get_provider_from_model(model), "")}'''

            try:
                if model in self.online_models.get('openai', []):
                    response = self._call_openai_api(prompt, model)
                elif model in self.online_models.get('claude', []):
                    response = self._call_claude_api(prompt, model)
                elif model in self.online_models.get('groq', []):
                    response = self._call_groq_api(prompt, model)
                else:
                    response = self._call_ollama_api(prompt, model, update_callback)

                result = self._parse_json_response(response)
                result["raw_llm_output"] = response

                if update_callback:
                    update_callback({
                        "raw_output": response,
                        "parsed_result": result,
                        "status": "completed"
                    })

                return result

            except Exception as e:
                logger.error(f"API call error: {str(e)}")
                return {
                    "score": 0,
                    "feedback": f"Error calling API: {str(e)}",
                    "improvements": ["API call failed"],
                    "breakdown": {"error": str(e)},
                    "raw_llm_output": str(e)
                }

        except Exception as e:
            error_msg = f"Error during grading: {str(e)}"
            logger.error(error_msg)
            return {
                "score": 0,
                "feedback": error_msg,
                "improvements": ["System error occurred"],
                "breakdown": {"error": str(e)},
                "raw_llm_output": str(e)
            }

    def _call_openai_api(self, prompt: str, model: str) -> str:
        """Call OpenAI API with JSON formatting"""
        if not self.openai_client:
            raise ValueError("OpenAI client not initialized")
        
        try:
            response = self.openai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a grading assistant. Respond with JSON only."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            return response.choices[0].message.content or "{}"
        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            raise

    def _call_claude_api(self, prompt: str, model: str) -> str:
        """Call Claude API with JSON formatting"""
        if not self.claude_client:
            raise ValueError("Claude client not initialized")
        
        try:
            response = self.claude_client.messages.create(
                model=model,
                max_tokens=2000,
                messages=[{
                    "role": "user",
                    "content": f"You are a grading assistant. Respond with JSON only.\n\n{prompt}"
                }]
            )
            
            if hasattr(response, 'content'):
                return response.content[0].text
            if hasattr(response, 'completion'):
                return response.completion
            return "{}"
            
        except Exception as e:
            logger.error(f"Claude API error: {str(e)}")
            raise

    def _call_groq_api(self, prompt: str, model: str) -> str:
        """Call Groq API with JSON formatting"""
        if not self.groq_api_key:
            raise ValueError("Groq API key not configured")
        
        try:
            headers = {
                "Authorization": f"Bearer {self.groq_api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": model,
                "messages": [
                    {"role": "system", "content": "You are a grading assistant. Respond with JSON only."},
                    {"role": "user", "content": prompt}
                ],
                "response_format": {"type": "json_object"}
            }
            
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.ok:
                return response.json().get("choices", [{}])[0].get("message", {}).get("content", "{}")
            else:
                raise Exception(f"Groq API error: {response.text}")
        except Exception as e:
            logger.error(f"Groq API error: {str(e)}")
            raise

    def _call_ollama_api(self, prompt: str, model: str, update_callback: Optional[Callable] = None) -> str:
        """Call Ollama API with JSON formatting"""
        try:
            messages = [
                Message(
                    role="system",
                    content="You are a grading assistant. Respond with JSON only."
                ),
                Message(
                    role="user",
                    content=prompt
                )
            ]
            
            options = {"format": "json"}
            
            full_response = ""
            response = ollama.chat(
                model=model,
                messages=messages,
                stream=True,
                options=options
            )
            
            for chunk in response:
                if isinstance(chunk, dict) and "message" in chunk:
                    content = chunk["message"].get("content", "")
                    full_response += content
                    
                    if update_callback:
                        update_callback({
                            "raw_output": full_response,
                            "status": "streaming"
                        })
            
            return full_response
            
        except Exception as e:
            logger.error(f"Ollama API error: {str(e)}")
            raise
