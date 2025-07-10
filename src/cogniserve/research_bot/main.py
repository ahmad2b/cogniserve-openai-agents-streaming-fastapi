import asyncio

from .manager import ResearchManager

async def main():
  query = "What is the future of AI?"
  report = await ResearchManager().run(query)
  print(report.markdown_report)
  
if __name__ == "__main__":
  asyncio.run(main())