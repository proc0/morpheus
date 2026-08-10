import os
from enum import Enum, auto
from typing import Optional
from pydantic import BaseModel, model_validator

class Provider(Enum):
	DEFAULT = auto()
	OLLAMA = auto()
	# ANTHROPIC = auto()
	GOOGLE = auto()

class Configuration(BaseModel):
	id: Provider = Provider.DEFAULT
	model: str = ""
	api_key_id: Optional[str] = None
	endpoint: Optional[str] = None

	api_key: str = ""
	url: str = ""

	@model_validator(mode='after')
	def validate(self, model):
		#TODO: check model type and raise Errors
		if self.api_key_id != None:
			key = os.environ.get(self.api_key_id)
			self.api_key = key if key != None else ""

		if self.endpoint != None:
			self.url = self.endpoint if self.endpoint != None else ""

		return self

DEFAULT_PROVIDER: dict[Provider, Configuration] = {
	Provider.DEFAULT: Configuration(),
	Provider.OLLAMA: Configuration(
		id=Provider.OLLAMA, 
		model="gemma4:31b", 
		endpoint="http://localhost:11434/api/chat"
	),
	# Provider.ANTHROPIC: Configuration(
	# 	id=Provider.ANTHROPIC,
	# 	model="claude-3-5-sonnet-20240620",
	# 	api_key_id="ANTHROPIC_API_KEY"
	# ),
	Provider.GOOGLE: Configuration(
		id=Provider.GOOGLE,
		model="gemini-3-flash-preview",
		api_key_id="GEMINI_API_KEY"
	)
}
