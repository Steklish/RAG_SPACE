from app.chroma_client import ChromaClient
from app.colors import INFO_COLOR, Colors
from app.local_generator import LocalGenerator
from app.thread_store import ThreadStore
from app.schemas import *


MAX_ITERATIONS = 3

class Agent:
    def __init__(self, generator: LocalGenerator, chroma_client: ChromaClient, thread_store : ThreadStore, language : str = "Russian"):
        self.generator = generator
        self.chroma_client = chroma_client
        self.thread_store = thread_store  
        self.language = language
    def user_intent(self, thread : Thread) -> IntentAnalysis:
        doc_list_text = ""
        for doc in self.chroma_client.get_all_documents():
            if doc.get('id') in thread.document_ids:
                doc_list_text += f"- {doc.get('name')}\n"

        history = "\n".join([f"{'User' if msg.sender == 'user' else 'Agent'}: {msg.content}" for msg in thread.history])

        
        prompt = (
            f"You are an expert at query expansion. Rewrite the user's query by enriching it with context "
            f"from the conversation history and available documents. The rewritten query should be a single, "
            f"self-contained question or statement optimized for semantic search."
            f"You also need to determine if the user's query can be answered directly without retrieval. If not need_for_retrieval should be true.\n\n"
            f"**Chat History:**\n{history}\n\n"
            f"**Available Documents:**\n{doc_list_text}\n\n"
            f"**User Query:** \"{thread.history[-1].content}\"\n\n"
            f"**Optimized Query:**"
        )
        print("Prompt for intent analysis:", prompt)
        response: IntentAnalysis = self.generator.generate(
            language=self.language,
            prompt=prompt,
            pydantic_model=IntentAnalysis
        )  
        print(f"Identified intent: {response.intent}, Need for retrieval: {response.need_for_retrieval}")
        return response

    def user_query(self, user_input: str, thread_id: str, iterate: bool = True):
        thread = self.thread_store.get_thread(thread_id)
        if not thread:
            raise ValueError("Thread not found")
        
        thread.history.append(UserMessage(sender="user", content=user_input))
        
        # We'll use the enriched query from the previous step here
        enriched_query_obj = self.user_intent(thread)
        
        if enriched_query_obj.need_for_retrieval and thread.document_ids:
            print(f"{INFO_COLOR} RAG USED {Colors.RESET}")
            retrieved_chunks_data = self.chroma_client.search_chunks(
                query_text=enriched_query_obj.intent, # Use the enriched query for search
                top_k=5,
                doc_ids=thread.document_ids
            )
            chunks_text = "\n".join(
                [f"<chunk index=\"{index}\" name=\"{chunk['metadata']['name']}\">\n{chunk['text']}\n</chunk>" for index, chunk in enumerate(retrieved_chunks_data)]
            )
            
            history = "\n".join([f"{'User' if msg.sender == 'user' else 'Agent'}: {msg.content}" for msg in thread.history])

            # --- REWORKED PROMPT ---
            prompt = (
                f"You are an AI assistant that answers questions based ONLY on the provided context. Follow these steps:\n"
                f"1. Synthesize a direct answer to the user's last query using the information in `<retrieved_chunks>`.\n"
                f"2. At the end of each sentence that uses information from a chunk, you MUST cite it using its index, like this: `This is a fact.`.\n"
                f"3. After writing the answer, determine if any part of the user's query remains unanswered. If another search could find more details, formulate a concise search query for the missing information in the `any_more_info_needed` field. If the answer is complete, leave that field empty.\n\n"
                f"---\n\n"
                f"**Chat History:**\n"
                f"{history}\n\n"
                f"**Retrieved Chunks:**\n"
                f"{chunks_text}\n\n"
                f"**User Query:** {thread.history[-1].content}"
            )

            print("Prompt for response with retrieval:", prompt)
            response = self.generator.generate(
                language=self.language,
                prompt=prompt,
                pydantic_model=ResponseWithRetrieval)
            
            retrieved_docs_map = {chunk['metadata']['doc_id']: chunk['metadata']['name'] for chunk in retrieved_chunks_data}
            retrieved_docs = [RetrievedDocument(id=doc_id, name=name) for doc_id, name in retrieved_docs_map.items()]

            thread.history.append(AgentMessage(sender="agent", content=response.answer, retrieved_docs=retrieved_docs))
            
            agent_response = AgentResponse(answer=response.answer, retrieved_docs=retrieved_docs)
            yield agent_response.model_dump_json()
            
            if response.any_more_info_needed and iterate:
                yield AgentResponse(answer="<internal>" + response.any_more_info_needed).model_dump_json()
                thread.history.append(AgentMessage(sender="agent", content=response.any_more_info_needed))
                yield from self.agent_query(0, thread, response.any_more_info_needed)
        else:
            # This branch remains the same, as it doesn't involve complex retrieval logic
            history = "\n".join([f"{'User' if msg.sender == 'user' else 'Agent'}: {msg.content}" for msg in thread.history])
            prompt = (
                f"You are a helpful assistant. Your task is to directly answer the user's question based on the provided chat history. "
                f"Do not explain your reasoning process. Provide a direct answer in the `answer` field.\n\n"
                f"<chat_history>\n"
                f"{history}\n"
                f"</chat_history>\n\n"
                f"Based on the user query, provide a comprehensive answer."
                f"<user_query> {thread.history[-1].content}\n </user_query>"
                f"<user_intent> {enriched_query_obj.intent}\n </user_intent>"
            )
            response = self.generator.generate(
                language=self.language,
                prompt=prompt,
                pydantic_model=ResponseWithoutRetrieval)
            thread.history.append(AgentMessage(sender="agent", content=response.answer))
            yield AgentResponse(answer=response.answer).model_dump_json()
        self.thread_store.save_thread(thread)
        
    def agent_query(self, iteration : int, thread : Thread, info_needed : str):
        if iteration >= MAX_ITERATIONS:
            yield AgentResponse(answer="<internal>Maximum iterations reached.").model_dump_json()
            return

        # In agent_query, we search all documents since the query is for new info
        retrieved_chunks_data = self.chroma_client.search_documents(
                query_text=info_needed,
                top_k=5
            )
        
        chunks_text = "\n".join(
            [f"<chunk index=\"{index}\" name=\"{chunk['metadata']['name']}\">\n{chunk['text']}\n</chunk>" for index, chunk in enumerate(retrieved_chunks_data)] # type: ignore
        )
        
        history = "\n".join([f"{'User' if msg.sender == 'user' else 'Agent'}: {msg.content}" for msg in thread.history])
        
        # --- REWORKED PROMPT ---
        prompt = (
            f"You are in a research loop to answer the original user query. Use the newly retrieved chunks to improve the answer. Follow these steps:\n"
            f"1. Synthesize a complete and updated answer to the user's original query using the chat history and the new `<retrieved_chunks>`.\n"
            f"2. At the end of each sentence that uses information from a NEW chunk, you MUST cite it using its index, like this: `This is a new fact.`.\n"
            f"3. After writing the new, complete answer, determine if any part of the query *still* remains unanswered. If another search could find more details, formulate a new, concise search query for the missing information in `any_more_info_needed`. If the answer is now complete, leave that field empty.\n\n"
            f"---\n\n"
            f"**Chat History (contains the original query):**\n"
            f"{history}\n\n"
            f"**Newly Retrieved Chunks:**\n"
            f"{chunks_text}\n\n"
        )

        response = self.generator.generate(
            language=self.language,
            prompt=prompt,
            pydantic_model=ResponseWithRetrieval)
        
        print(f"Iteration {iteration} - Agent response: {response.answer}")

        retrieved_docs_map = {chunk['metadata']['doc_id']: chunk['metadata']['name'] for chunk in retrieved_chunks_data} # type: ignore
        retrieved_docs = [RetrievedDocument(id=doc_id, name=name) for doc_id, name in retrieved_docs_map.items()]

        thread.history.append(AgentMessage(sender="agent", content=response.answer, retrieved_docs=retrieved_docs, follow_up=True))
        
        agent_response = AgentResponse(answer=response.answer, retrieved_docs=retrieved_docs, follow_up=True)
        yield agent_response.model_dump_json()
        
        if response.any_more_info_needed:
            yield AgentResponse(answer="<internal>" + response.any_more_info_needed).model_dump_json()
            thread.history.append(AgentMessage(sender="agent", content=response.any_more_info_needed, retrieved_docs=retrieved_docs, follow_up=True))
            yield from self.agent_query(iteration + 1, thread, response.any_more_info_needed)