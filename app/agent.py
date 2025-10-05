from app.chroma_client import ChromaClient
from app.local_generator import LocalGenerator
from app.thread_store import ThreadStore
from app.schemas import *


MAX_ITERATIONS = 3

class Agent:
    def __init__(self, generator: LocalGenerator, chroma_client: ChromaClient, thread_store : ThreadStore):
        self.generator = generator
        self.chroma_client = chroma_client
        self.thread_store = thread_store  
    
    def user_intent(self, thread) -> IntentAnalysis:
        prompt = "\n".join(thread.history) + f"\nIdentify the user's intent of the last request and whether retrieval is needed to answer the query."
        response : IntentAnalysis= self.generator.generate(
            prompt=prompt,
            pydantic_model=IntentAnalysis)  
        print(f"Identified intent: {response.intent}, Need for retrieval: {response.need_for_retrieval}")
        return response
    
    
    def user_query(self, user_input: str, thread_id: str):
        thread = self.thread_store.get_thread(thread_id)
        if not thread:
            raise ValueError("Thread not found")
        
        thread.history.append(f"User: {user_input}")
        
        intent = self.user_intent(thread_id)
        
        if intent.need_for_retrieval:
            
            retrieved_chunks = self.chroma_client.search_documents(
                query_text=user_input,
                top_k=5
            )
            prompt = "\n".join(thread.history) + f"\nBased on the identified intent: {intent.intent}, and the following retrieved information: {retrieved_chunks}, provide a comprehensive answer. If more information is needed, specify what is needed."
            response = self.generator.generate(
                prompt=prompt,
                pydantic_model=ResponseWithRetrieval)
            thread.history.append(f"Agent: {response.answer}")
            yield response.answer
            
            
            if response.any_more_info_needed:
                yield "<internal>" + response.any_more_info_needed
                thread.history.append(f"Agent: {response.any_more_info_needed}")
                yield from self.agent_query(0, thread, response.any_more_info_needed)
        else:
            prompt = "\n".join(thread.history) + f"\nBased on the identified intent: {intent.intent}, provide a comprehensive answer."
            response = self.generator.generate(
                prompt=prompt,
                pydantic_model=ResponseWithoutRetrieval)  
            yield response.answer
        self.thread_store.save_thread(thread)
        
    def agent_query(self, iteration : int, thread : Thread, info_needed : str):
        if iteration >= MAX_ITERATIONS:
            yield "<internal>Maximum iterations reached."

        retrieved_chunks = self.chroma_client.search_documents(
                query_text=info_needed,
                top_k=5
            )
        prompt = "\n".join(thread.history) + f"\nBased on the previous conversation and the following retrieved information: {retrieved_chunks}, provide a comprehensive answer. If more information is needed, specify what is needed."
        response = self.generator.generate(
            prompt=prompt,
            pydantic_model=ResponseWithoutRetrieval)  
        print(f"Iteration {iteration} - Agent response: {response.answer}")
        thread.history.append(f"Agent: {response.answer}")
        yield response.answer
        