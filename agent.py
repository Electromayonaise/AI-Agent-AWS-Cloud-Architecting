from langchain_groq import ChatGroq
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from tools import resize_rotate_flip_image_tool
from config import GROQ_API_KEY, MODEL_NAME, LLM_TEMPERATURE, S3_BUCKET_SOURCE, SIZE_PRESETS

SYSTEM_PROMPT = f"""You are an AI assistant that helps users process images stored in Amazon S3.

When a user asks to resize, rotate, flip, or transform an image, use the resize_rotate_flip_image_tool.

Available size presets:
- thumbnail: {SIZE_PRESETS['thumbnail'][0]}x{SIZE_PRESETS['thumbnail'][1]} pixels
- medium:    {SIZE_PRESETS['medium'][0]}x{SIZE_PRESETS['medium'][1]} pixels
- large:     {SIZE_PRESETS['large'][0]}x{SIZE_PRESETS['large'][1]} pixels

Words like "miniatura" or "small" map to "thumbnail"; "mediano" maps to "medium"; "grande" or "large" maps to "large".
Custom dimensions are also supported: extract width and height from the user's request.

Rotation is clockwise. If the user says "rotate 90°", pass rotation=90.
Flip horizontal = mirror effect. Flip vertical = upside-down.

Default S3 source bucket: {S3_BUCKET_SOURCE}
If the user does not specify a bucket, use the default.

Always confirm the result and output S3 location after the tool runs.
Answer in the same language the user used."""

llm = ChatGroq(
    model=MODEL_NAME,
    temperature=LLM_TEMPERATURE,
    groq_api_key=GROQ_API_KEY,
)

tools = [resize_rotate_flip_image_tool]

prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", "{input}"),
    MessagesPlaceholder("agent_scratchpad"),
])

agent = create_tool_calling_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)


def run_agent(user_input: str) -> str:
    result = agent_executor.invoke({"input": user_input})
    return result["output"]


if __name__ == "__main__":
    print("=" * 60)
    print("  AI Image Processing Agent - AWS")
    print("  Type 'exit' or 'salir' to quit")
    print("=" * 60)
    print()

    while True:
        try:
            user_input = input("You > ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nBye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit", "salir"):
            print("Bye!")
            break

        response = run_agent(user_input)
        print(f"\nAgent > {response}\n")
