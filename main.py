import os
from agents import Runner , RunConfig,OpenAIChatCompletionsModel,AsyncOpenAI,Agent
import chainlit as cl
from dotenv import load_dotenv
from pinecone import Pinecone , ServerlessSpec
import PyPDF2
from openai.types.responses import ResponseTextDeltaEvent 


load_dotenv()

#   Step 1  loading envoirments veriables

Gemini_Api = os.getenv("API_KEY")
Pincecone_Api = os.getenv("PINECONE_API_KEY")
Pinecone_Index = "cv-index"

#  Step 2 Steup Gemini Agents

provider = AsyncOpenAI(
    api_key=Gemini_Api,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

Model = OpenAIChatCompletionsModel(
    model="gemini-2.0-flash",
    openai_client=provider,
)

runconfig = RunConfig(
    model=Model,
    model_provider=provider,
    tracing_disabled=True,
)

System = Agent(
    name="Muhammad Waseem",
    instructions="You are a helpful assistant who answers questions based on a user's CV. If the answer is not found in the CV, say it clearly.",
)

# Step 3 Pinecone setup

pc = Pinecone(api_key=Pincecone_Api)

# step 3A create index in pinecone
async def create_index_pinecone(name : str):
    
    pc.create_index(
        name=name,
        dimension=768,
        metric = 'euclidean',
        spec=ServerlessSpec(cloud='aws' , region='us-east-1')
    )


index = pc.Index(Pinecone_Index)

#  step 4 pdf extraction System

async def text_extraction_from_pdf(file_path : str) -> str:
    text = ""
    try:
        with open(file_path , "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text += page.extract_text() or ""
    except Exception as e:
        print(f"We can't Extract that pdf as error {e}")
        return None
    return text

# Step 5 embeding Generator

async def embedding_generator(text : str)-> list[float]:
    try:
        response = await provider.embeddings.create(
            input= text,
            model="embedding-001",
        ) 
        return response.data[0].embedding
    except Exception as e:
        print(f"Can't generate embeddings as error {e}")
        return None
    
#  Step 6 Pinecone Searches
    

async def pincone_searches(query : str , max : int = 3) -> list:

    query_embedded = await embedding_generator(query)
    result = index.query(vector=query_embedded , top_k=max , include_metadata=True)
    return result.matches


@cl.on_chat_start
async def handle_chat_start():
    if Pinecone_Index not in pc.list_indexes().names():
        cl.user_session.set("upload PDF" , False)
        
    
        

        response = await cl.AskFileMessage(
            content="Upload PDF CV",
            accept=[".pdf"],
            max_files=1,
            max_size_mb=5
        ).send()
        if not response:
            await cl.Message(content="Failed to Uplaod CV Refresh and Again").send()
            return
        file = response[0]
        
        await create_index_pinecone(Pinecone_Index)
        text = await text_extraction_from_pdf(file.path)

        if text is None:
            await cl.Message(content="Text not found in pdf please check your PDF").send()
            return
        
        embeddings  = await embedding_generator(text)

        if embeddings is None:
            await cl.Message(content="Error in generating embadings").send()
            return
        try:
            index.upsert(vectors=[(file.name , embeddings , {"text": text})])
            await cl.Message(content="CV uploaded to Data_Base Sucessfully").send()
            # cl.user_session.set("upload PDF" , True)
        except Exception as e:
            await cl.Message(content=f"Failed to upload Cv in data base as error {e}").send()



        
@cl.on_message
async def main(message : cl.Message):
    result = await pincone_searches(message.content)
    if result:
        contenxt = "\n".join([match.metadata["text"] for match in result])
        prompt = f"Answer the following base of this context answer should cleare help user if any thing Out and ask question to clearify and if confusing simply denie: \nquestion {message.content} \n context : {contenxt}"
        msg = cl.Message(content="")
        await msg.send()
        try:
            llm_output = Runner.run_streamed(
                System,
                input=prompt,
                run_config=runconfig,
            )
            async for chunk in llm_output.stream_events():
                if chunk.type == "raw_response_event" and isinstance(chunk.data ,ResponseTextDeltaEvent):
                      await msg.stream_token(chunk.data.delta)
                
        except Exception as e:
            await cl.Message(content=f"LLM Fails To Return an Answer as error {e}").send()
    else:
        await cl.Message(content="No Matched or Releavent Info Found In CV").send()


