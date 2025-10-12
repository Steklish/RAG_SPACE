import time
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
        
    def history_to_payload(self, thread: Thread) -> LLamaMessageHistory:
        messages = []
        for msg in thread.history:
            if msg.sender == "user":
                messages.append(UserLamaMessage(content=msg.content))
            elif msg.sender == "agent":
                messages.append(ModelLamaMessage(content=msg.content))
            elif msg.sender == "system":
                messages.append(SystemLamaMessage(content=msg.content))
        return LLamaMessageHistory(messages=messages)
        
    def user_intent(self, thread : Thread, temperature:float = 0.5) -> IntentAnalysis:
        doc_list_text = ""
        for doc in self.chroma_client.get_all_documents():
            if doc.get('id') in thread.document_ids: # type: ignore
                doc_list_text += f"- {doc.get('name')}\n"


        example_query = [{'role': 'user', 'content': 'опиши по порядку все содержание файла ПЗ'}, {'role': 'model', 'content': 'Пожалуйста, предоставьте больше информации о файле ПЗ.  Мне нужно знать, что это за файл.  В частности, мне нужно увидеть содержимое файла, чтобы я мог описать его функциональность и назначение.'},  {'role': 'model', 'content': 'Проект - устройство для измерения расстояний, использующее HC-SR04, предназначенное для работы с Raspberry Pi, с точностью до 4 м и низким уровнем стоимости.'}, {'role': 'user', 'content': 'hi there'}]
        example_response = {
            "enhanced_query": "Пользователь поприветствовал систему на английском языке, сказав «hi there», что не связано с предыдущим контекстом обсуждения проекта по измерению расстояний, не требует анализа содержимого файла ПЗ и не связан с техническими деталями проекта.",
            "need_for_retrieval": False
            }

        system_prompt = (
            f"""You are an expert at query expansion. Rewrite the user's query by enriching it with context 
            If any documents are mentioned you MUST set `need_for_retrieval` to true.
            from the conversation history and available documents. The rewritten query should be a single, 
            self-contained question or statement. It should be detailed and specific, incorporating relevant information from the chat history and documents. It should be grammatically correct and coherent.\n\n
            You also need to determine if the user's query can be answered directly without retrieval. If not need_for_retrieval should be true.\n\n
            If user mentions any documant or topic from availabel or spmething that is not present in the current context you must set need_for_retrieval as true.
            **Available Documents:**\n{doc_list_text}\n\n
            Dont ask for more information, just rewrite the query.\n\n
            <Example>
            example query(conversation history): {example_query} 
            example response: {example_response} 
            </Example>
            """
        )
        
        prompt = f"""
        Here is the conversation history and you must determine what exactly user wants to get from the data retrieval system with their latest query.
        <conversation history>
        {self.history_to_payload(thread)}
        </conversation history>
        """ 
        print("Prompt for intent analysis:", system_prompt)
        print("History for intent analysis:", self.history_to_payload(thread).to_dict())
        response: IntentAnalysis = self.generator.generate_one_shot(
            system_prompt=system_prompt,
            prompt=prompt,
            language=self.language,
            pydantic_model=IntentAnalysis,
            temperature=temperature
        )  
        print(f"Identified intent: {response.enhanced_query}, Need for retrieval: {response.need_for_retrieval}")
        return response

    def user_query(self, user_input: str, thread_id: str, iterate: bool = True, temperature: float = 0.7):
        thread = self.thread_store.get_thread(thread_id)
        if not thread:
            raise ValueError("Thread not found")
        
        thread.history.append(UserMessage(sender="user", content=user_input))
        
        # We'll use the enriched query from the previous step here
        enriched_query_obj = self.user_intent(thread)
        
        if enriched_query_obj.need_for_retrieval and thread.document_ids:
            print(f"{INFO_COLOR} RAG USED {Colors.RESET}")
            retrieved_chunks_data = self.chroma_client.search_chunks(
                query_text=enriched_query_obj.enhanced_query + " Оriginal text follows:" + thread.history[-1].content, # Use the enriched query for search
                top_k=5,
                doc_ids=thread.document_ids
            )
            chunks_text = "\n".join(
                [f"<chunk index=\"{index}\" name=\"{chunk['metadata']['name']}\">\n{chunk['text']}\n</chunk>" for index, chunk in enumerate(retrieved_chunks_data)]
            )

            system_prompt = (
                f"""
                You are an AI assistant that answers questions based ONLY on the provided context. Follow these steps:\n
                1. Provide a concise, direct answer to the user's query based strictly on the information in `<likely_referenced_data>`. You are allowed to use  MarkDown tags only inside `answer` filed.\n
                2. After answering, check if any part of the user's query remains unanswered.\n
                3. For requesting additional details, generate a focused search query in the `any_more_info_needed` field for the next iteration.\n
                if the answer is incomplete YOU MUST ITERATE and place in the `any_more_info_needed` field the information necessary to continue refining the answer in the next step.\n\n
                <likely_referenced_data>
                {chunks_text}\n\n
                </likely_referenced_data>
                """
            )
            prompt = f"""
            Here is the user query that you should fulfill using the information provided.
            <user_query>
            {enriched_query_obj.enhanced_query}
            </user_query>
            """ 

            # print("Prompt for response with retrieval:", prompt)
            response = self.generator.generate_one_shot(
                system_prompt=system_prompt,
                prompt=prompt,
                language=self.language,
                pydantic_model=ResponseWithRetrieval,
                temperature=temperature)
            
            retrieved_docs_map = {chunk['metadata']['doc_id']: chunk['metadata']['name'] for chunk in retrieved_chunks_data}
            retrieved_docs = [RetrievedDocument(id=doc_id, name=name) for doc_id, name in retrieved_docs_map.items()]

            thread.history.append(AgentMessage(sender="agent", content=response.answer, retrieved_docs=retrieved_docs))
            
            agent_response = AgentResponse(answer=response.answer, retrieved_docs=retrieved_docs, follow_up=not(response.any_more_info_needed is None))
            yield agent_response.model_dump_json()
            
            if response.any_more_info_needed and iterate:
                yield AgentResponse(answer="<internal>" + response.any_more_info_needed).model_dump_json()
                thread.history.append(AgentMessage(sender="agent", content=response.any_more_info_needed))
                yield from self.agent_query(0, thread, response.any_more_info_needed)
        else:
            
            print(f"{INFO_COLOR} NO RAG {Colors.RESET}")
            system_prompt = (
                f"You are a helpful assistant. Your task is to directly answer the user's question based on the provided chat history. "
                f"Do not explain your reasoning process. Provide a direct answer in the `answer` field.\n\n"
                f"Based on the user query, provide a comprehensive answer."
            )
            response = self.generator.generate_with_payload(
                system_prompt=system_prompt,
                language=self.language,
                pydantic_model=ResponseWithoutRetrieval,
                payload=self.history_to_payload(thread))
            
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
        system_prompt = (
            f"You are in a research loop to answer the original user query. Use the newly retrieved chunks to improve the answer. Follow these steps:\n"
            f"1. Synthesize a complete and updated answer to the user's original query using the chat history and the new `<retrieved_chunks>`.\n"
            f"2. At the end of each sentence that uses information from a NEW chunk, you MUST cite it using its index, like this: `This is a new fact.`.\n"
            f"3. After writing the new, complete answer, determine if any part of the query *still* remains unanswered. If another search could find more details, formulate a new, concise search query for the missing information in `any_more_info_needed`. If the answer is now complete, leave that field empty.\n\n"
            f"---\n\n"
            f"**Newly Retrieved Chunks:**\n"
            f"{chunks_text}\n\n"
        )

        response = self.generator.generate_with_payload(
            system_prompt=system_prompt,
            language=self.language,
            payload=self.history_to_payload(thread),
            pydantic_model=ResponseWithRetrieval)
        
        print(f"{INFO_COLOR}Iteration {iteration} {Colors.RESET} - Agent response: {response.answer}")

        retrieved_docs_map = {chunk['metadata']['doc_id']: chunk['metadata']['name'] for chunk in retrieved_chunks_data} # type: ignore
        retrieved_docs = [RetrievedDocument(id=doc_id, name=name) for doc_id, name in retrieved_docs_map.items()]

        thread.history.append(AgentMessage(sender="agent", content=response.answer, retrieved_docs=retrieved_docs, follow_up=True))
        
        agent_response = AgentResponse(answer=response.answer, retrieved_docs=retrieved_docs, follow_up=True)
        yield agent_response.model_dump_json()
        
        if response.any_more_info_needed:
            yield AgentResponse(answer="<internal>" + response.any_more_info_needed).model_dump_json()
            thread.history.append(AgentMessage(sender="agent", content=response.any_more_info_needed, retrieved_docs=retrieved_docs, follow_up=True))
            yield from self.agent_query(iteration + 1, thread, response.any_more_info_needed)

    def simple_query(self, user_input: str, thread_id: str):
        thread = self.thread_store.get_thread(thread_id)
        if not thread:
            raise ValueError("Thread not found")

        thread.history.append(UserMessage(sender="user", content=user_input))

        context_for_prompt = ""
        retrieved_docs = []
        
        if thread.document_ids:
            print(f"{INFO_COLOR} RAG USED (Simple Query) {Colors.RESET}")
            retrieved_chunks_data = self.chroma_client.search_chunks(
                query_text=user_input,
                top_k=3,
                doc_ids=thread.document_ids
            )
            # Format context for the model and collect document metadata
            context_for_prompt = "\n\n".join(
                [f"Source Document: {chunk['metadata']['name']}\nContent:\n{chunk['text']}" for chunk in retrieved_chunks_data]
            )
            
            # Create a unique list of retrieved documents for the response
            retrieved_docs_map = {chunk['metadata']['doc_id']: chunk['metadata']['name'] for chunk in retrieved_chunks_data}
            retrieved_docs = [RetrievedDocument(id=doc_id, name=name) for doc_id, name in retrieved_docs_map.items()]

        # Create a simple message history for the prompt
        messages_for_prompt = self.history_to_payload(thread)

        # Add the retrieved context and instructions to the system prompt
        system_prompt_parts = ["You are a helpful assistant. Answer the user's question based on the conversation history."]
        if context_for_prompt:
            system_prompt_parts.append(
                "You have been provided with the following context from relevant documents. "
                "When you use information from this context, you MUST cite the source document's name, for example: [Source: document_name.pdf]."
            )
            messages_for_prompt.messages.insert(0, SystemLamaMessage(role="system", content=f"--- CONTEXT ---\n{context_for_prompt}\n--- END CONTEXT ---"))

        messages_for_prompt.messages.insert(0, SystemLamaMessage(role="system", content="\n".join(system_prompt_parts)))

        # Use the simpler `complete` method for direct text generation
        response_text = self.generator.complete(
            payload=messages_for_prompt,
            temperature=0.7
        )

        # Save the full agent message with retrieved docs to history
        thread.history.append(AgentMessage(sender="agent", content=response_text, retrieved_docs=retrieved_docs))
        self.thread_store.save_thread(thread)

        # Yield the structured response
        agent_response = AgentResponse(answer=response_text, retrieved_docs=retrieved_docs)
        yield agent_response.model_dump_json()