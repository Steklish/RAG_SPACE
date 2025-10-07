from app.chroma_client import ChromaClient
from app.colors import INFO_COLOR, Colors
from app.local_generator import LocalGenerator
from app.thread_store import ThreadStore
from app.schemas import *


MAX_ITERATIONS = 3

class Agent:
    def __init__(self, generator: LocalGenerator, chroma_client: ChromaClient, thread_store : ThreadStore, prim_language : str = "Русский"):
        self.generator = generator
        self.chroma_client = chroma_client
        self.thread_store = thread_store  
        self.primary_language = prim_language
    
    def user_intent(self, thread : Thread) -> IntentAnalysis:
        doc_list_text = ""
        for doc in self.chroma_client.get_all_documents():
            if doc.get('id') in thread.document_ids:
                doc_list_text += f"- {doc.get('name')}\n"

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
        *   **Intent:** "Summarize the 'Project Alpha' document."
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
            f"{'\\n'.join(thread.history)}\n"
            f"</chat_history>\n\n"
            f"Here are the available documents that the user might be referencing:\n"
            f"{doc_list_text}\n\n"
            f"If the user's question could be related to any of these documents, you must set `need_for_retrieval` to `True`.\n\n"
            f"{examples}\n\n"
            f"Based on the information above, analyze the last user request and determine the intent and whether retrieval is needed."
        )
        print("Prompt for intent analysis:", prompt)
        response: IntentAnalysis = self.generator.generate(
            language=self.primary_language,
            prompt=prompt,
            pydantic_model=IntentAnalysis
        )  
        print(f"Identified intent: {response.intent}, Need for retrieval: {response.need_for_retrieval}")
        return response
    
    def user_query(self, user_input: str, thread_id: str, iterate: bool = True):
        thread = self.thread_store.get_thread(thread_id)
        if not thread:
            raise ValueError("Thread not found")
        
        thread.history.append(f"User: {user_input}")
        
        intent = self.user_intent(thread)
        
        if intent.need_for_retrieval:
            print(f"{INFO_COLOR} RAG USED {Colors.RESET}")
            retrieved_chunks_data = self.chroma_client.query_chunks(
                query_text=user_input,
                top_k=5
            )
            chunks_text = "\n".join(
                [f"<chunk {index} name=\"{chunk['metadata']['name']}\"> {chunk['text']} </chunk {index}>\n" for index, chunk in enumerate(retrieved_chunks_data)]
            )
            
            examples = """
                Here are some examples of how to respond:

                **Example 1: Sufficient Information**
                *   **User Request:** "What is the subject of the reports?"
                *   **Retrieved Chunks:** "This report for the course 'Robotics Systems' covers..."
                *   **Correct JSON Output:**
                    ```json
                    {
                      "answer": "The reports are for the 'Robotics Systems' course.",
                      "any_more_info_needed": null
                    }
                    ```

                **Example 2: Insufficient Information**
                *   **User Request:** "What were the project deadlines?"
                *   **Retrieved Chunks:** "The project required building a line-following robot. The final report should include a circuit diagram."
                *   **Correct JSON Output:**
                    ```json
                    {
                      "answer": "The provided documents mention the project requirements, such as building a line-following robot, but they do not specify the deadlines.",
                      "any_more_info_needed": "Specific project deadlines or dates."
                    }
                    ```
                """

            prompt = (
                f"You are a helpful assistant. Your task is to directly answer the user's question based on the provided chat history and retrieved information. "
                f"Do not explain your reasoning process. Provide a direct answer in the `answer` field.\n\n"
                f"If the retrieved information is insufficient to answer the question, state that in the `answer` field and use the `any_more_info_needed` field to specify what information is missing.\n\n"
                f"{examples}\n\n"
                f"---\n\n"
                f"<chat_history>\n"
                f"{'\\n'.join(thread.history)}\n"
                f"</chat_history>\n\n"
                f"<retrieved_chunks>\n"
                f"{chunks_text}\n"
                f"</retrieved_chunks>\n\n"
                f"Based on the identified intent: '<intent>{intent.intent}</intent>', and the retrieved information, provide a comprehensive answer."
            )
            print("Prompt for response with retrieval:", prompt)
            response = self.generator.generate(
                language=self.primary_language,
                prompt=prompt,
                pydantic_model=ResponseWithRetrieval)
            thread.history.append(f"Agent: {response.answer}")
            yield response.answer
            
            if response.any_more_info_needed and iterate:
                yield "<internal>" + response.any_more_info_needed
                thread.history.append(f"Agent: {response.any_more_info_needed}")
                yield from self.agent_query(0, thread, response.any_more_info_needed)
        else:
            prompt = (
                f"You are a helpful assistant. Based on the chat history, provide a comprehensive and informative answer to the user's last request.\n\n"
                f"<chat_history>\n"
                f"{'\\n'.join(thread.history)}\n"
                f"</chat_history>\n\n"
                f"Based on the identified intent: '{intent.intent}', provide a comprehensive answer."
            )
            response = self.generator.generate(
                language=self.primary_language,
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
            language=self.primary_language,
            prompt=prompt,
            pydantic_model=ResponseWithRetrieval)  
        print(f"Iteration {iteration} - Agent response: {response.answer}")
        thread.history.append(f"Agent: {response.answer}")
        yield response.answer
        if response.any_more_info_needed:
            yield "<internal>" + response.any_more_info_needed
            thread.history.append(f"Agent: {response.any_more_info_needed}")
            yield from self.agent_query(iteration + 1, thread, response.any_more_info_needed)