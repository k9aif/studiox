from k9_aif_abb.k9_adapters.crewai import K9CrewAIAdapter

class DummyCrew:
    def kickoff(self, inputs=None):
        return {"output": f"Dummy CrewAI ran with: {inputs}"}

crew = DummyCrew()

adapter = K9CrewAIAdapter(crew=crew)

result = adapter.execute({
    "message": "Summarize weather trends for Atlanta",
    "intent": "weather_assist",
    "metadata": {"source": "smoke_test"}
})

print(result)