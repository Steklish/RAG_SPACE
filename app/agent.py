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

        # Few-shot examples
        examples = """
        Here are some examples of how to identify the user's intent:

        **Example 1: Simple Greeting**
        *   **User Request:** "Привет"
        *   **Intent:** "Greeting"
        *   **Need for Retrieval:** False

        **Example 2: Specific Question with Document Context**
        *   **User Request:** "Summarize the main points of the 'Project Alpha' document."
        *   **Available Documents:** ["Project Alpha.pdf", "meeting_notes.txt"]
        *   **Intent:** "Summarize the main points of the 'Project Alpha' document."
        *   **Need for Retrieval:** True

        **Example 3: Vague Question without Clear Document Context**
        *   **User Request:** "What were the key takeaways from the last meeting?"
        *   **Available Documents:** ["Project Alpha.pdf", "meeting_notes.txt"]
        *   **Intent:** "Inquire about key takeaways from the last meeting."
        *   **Need for Retrieval:** True (The model should search the documents for relevant information)

        **Example 4: General Knowledge Question**
        *   **User Request:** "What is the capital of France?"
        *   **Available Documents:** []
        *   **Intent:** "General knowledge question about the capital of France."
        *   **Need for Retrieval:** False
        """
        
        prompt = (
            f"You are an expert at analyzing user intent. Your task is to identify the user's intent from their last request "
            f"and determine if retrieval is necessary to provide an accurate answer. Retrieval is generally required for any question "
            f"that is not a simple greeting or a general knowledge query that can be answered without external context.\n\n"
            f"<chat_history>\n"
            f"{history}\n"
            f"</chat_history>\n\n"
            f"Here are the available documents that the user might be referencing:\n"
            f"{doc_list_text}\n\n"
            f"If the user's question could be related to any of these documents, you must set `need_for_retrieval` to `True`.\n\n"
            f"{examples}\n\n"
            f"Based on the information above, analyze the last user request and determine the intent and whether retrieval is needed."
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
        
        intent = self.user_intent(thread)
        
        if intent.need_for_retrieval and thread.document_ids:
            print(f"{INFO_COLOR} RAG USED {Colors.RESET}")
            retrieved_chunks_data = self.chroma_client.search_chunks(
                query_text=intent.intent,
                top_k=5,
                doc_ids=thread.document_ids
            )
            chunks_text = "\n".join(
                [f"<chunk {index} name=\"{chunk['metadata']['name']}\"> {chunk['text']} </chunk {index}>\n" for index, chunk in enumerate(retrieved_chunks_data)]
            )
            
            history = "\n".join([f"{'User' if msg.sender == 'user' else 'Agent'}: {msg.content}" for msg in thread.history])


            prompt = (
                f"You are a helpful assistant. Your task is to directly answer the user's question based on the provided chat history and retrieved information. "
                f"Do not explain your reasoning process. Provide a direct answer in the `answer` field.\n\n"
                f"If the retrieved information is insufficient to answer the question, state that in the `answer` field and use the `any_more_info_needed` field to specify what information is missing.\n\n If the information from a chunk was relevant to the answer, reference the chunk by its index and name in your response. with <chunk index=_>. Exaple <chunk index=1>"
                f"---\n\n"
                f"<chat_history>\n"
                f"{history}\n"
                f"</chat_history>\n\n"
                f"<retrieved_chunks>\n"
                f"{chunks_text}\n"
                f"</retrieved_chunks>\n\n"
                f"Based on the user query, and the retrieved information, provide a comprehensive answer, referencing sources as needed."
                f"<user_query> {thread.history[-1].content}\n </user_query>"
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
            history = "\n".join([f"{'User' if msg.sender == 'user' else 'Agent'}: {msg.content}" for msg in thread.history])
            prompt = (
                f"You are a helpful assistant. Your task is to directly answer the user's question based on the provided chat history and retrieved information. "
                f"Do not explain your reasoning process. Provide a direct answer in the `answer` field.\n\n"
                f"If the retrieved information is insufficient to answer the question, state that in the `answer` field and use the `any_more_info_needed` field to specify what information is missing.\n\n If the information from a chunk was relevant to the answer, reference the chunk by its index and name in your response. with <chunk index=_>. Exaple <chunk index=1>"
                f"<chat_history>\n"
                f"{history}\n"
                f"</chat_history>\n\n"
                f"Based on the user query, and the retrieved information, provide a comprehensive answer, referencing sources as needed."
                f"<user_query> {thread.history[-1].content}\n </user_query>"
                f"<user_intent> {intent.intent}\n </user_intent>"
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

        retrieved_chunks_data = self.chroma_client.search_documents(
                query_text=info_needed,
                top_k=5
            )
        
        chunks_text = "\n".join(
            [f"<chunk {index} name=\"{chunk['metadata']['name']}\"> {chunk['text']} </chunk {index}>\n" for index, chunk in enumerate(retrieved_chunks_data)] # type: ignore
        )
        
        history = "\n".join([f"{'User' if msg.sender == 'user' else 'Agent'}: {msg.content}" for msg in thread.history])
        
        prompt = (
            f"You are a helpful assistant. Your task is to directly answer the user's question based on the provided chat history and newly retrieved information. "
            f"Do not explain your reasoning process. Provide a direct answer in the `answer` field.\n\n"
            f"If the retrieved information is insufficient to answer the question, state that in the `answer` field and use the `any_more_info_needed` field to specify what information is missing.\n\n"
            f"<chat_history>\n{history}\n</chat_history>\n\n"
            f"<retrieved_chunks>\n{chunks_text}\n</retrieved_chunks>\n\n"
            f"Based on the user query and the retrieved information, provide a comprehensive answer, referencing sources as needed."
        )

        response = self.generator.generate(
            language=self.language,
            prompt=prompt,
            pydantic_model=ResponseWithRetrieval)
        
        print(f"Iteration {iteration} - Agent response: {response.answer}")

        retrieved_docs_map = {chunk['metadata']['doc_id']: chunk['metadata']['name'] for chunk in retrieved_chunks_data} # type: ignore
        retrieved_docs = [RetrievedDocument(id=doc_id, name=name) for doc_id, name in retrieved_docs_map.items()]

        thread.history.append(AgentMessage(sender="agent", content=response.answer, retrieved_docs=retrieved_docs))
        
        agent_response = AgentResponse(answer=response.answer, retrieved_docs=retrieved_docs)
        yield agent_response.model_dump_json()
        
        if response.any_more_info_needed:
            yield AgentResponse(answer="<internal>" + response.any_more_info_needed).model_dump_json()
            thread.history.append(AgentMessage(sender="agent", content=response.any_more_info_needed, retrieved_docs=retrieved_docs))
            yield from self.agent_query(iteration + 1, thread, response.any_more_info_needed)