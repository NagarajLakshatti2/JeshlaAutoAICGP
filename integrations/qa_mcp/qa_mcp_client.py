import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():

    print("1. Starting qa_mcp client...")

    server_params = StdioServerParameters(
        command=sys.executable,
        args=[
            str(
                Path(__file__).resolve().with_name(
                    "qa_mcp_server.py"
                )
            )
        ],
    )

    print("2. Starting qa_mcp server...")

    async with stdio_client(server_params) as (read, write):

        print("3. Server process started")

        async with ClientSession(read, write) as session:

            print("4. Initializing qa_mcp session...")

            await session.initialize()

            print("5. qa_mcp connection initialized")

            # --------------------------------
            # TOOL
            # --------------------------------

            tools = await session.list_tools()

            print("\nAvailable tools:")

            for tool in tools.tools:
                print("-", tool.name)

            result = await session.call_tool(
                "get_test_case",
                {
                    "test_id": "QA-101"
                }
            )

            print("\nTool result:")

            if result.is_error:
                print("❌ qa_mcp Tool failed")

                for content in result.content:
                    print("Error:", content.text)

            else:
                print("✅ qa_mcp Tool successful")

                for content in result.content:
                    print(content.text)

            # --------------------------------
            # RESOURCE TEMPLATE
            # --------------------------------

            templates = await session.list_resource_templates()

            print("\nAvailable resource templates:")

            for template in templates.resource_templates:
                print("-", template.uri_template)

            # --------------------------------
            # READ RESOURCE
            # --------------------------------

            resource_result = await session.read_resource(
                "testcase://QA-101"
            )

            print("\nResource result:")

            for content in resource_result.contents:
                print(content.text)

            # --------------------------------
            # PROMPT
            # --------------------------------

            prompts = await session.list_prompts()

            print("\nAvailable prompts:")

            for prompt in prompts.prompts:
                print("-", prompt.name)

            # Get generate_cucumber prompt
            prompt_result = await session.get_prompt(
                "generate_cucumber",
                arguments={
                    "test_id": "QA-101"
                }
            )

            print("\nPrompt result:")

            for message in prompt_result.messages:
                print(message.content)



if __name__ == "__main__":
    asyncio.run(main())