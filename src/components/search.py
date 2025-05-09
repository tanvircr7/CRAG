


# Search Tool  ----------------------------------------------------------------------------------------------------
def create_search_tool():
    ### Search
    from langchain_community.tools.tavily_search import TavilySearchResults

    web_search_tool = TavilySearchResults(k=3)  
    return web_search_tool
