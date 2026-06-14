from langchain_core.tools import tool

from agents.dance_agent import analyze_dance


@tool
def dance_analysis_tool(user_input: str) -> str:
    """
    分析使用者的舞蹈動作問題，提供結構化的評分與改善建議。
    
    Args:
        user_input: 使用者對自己舞蹈問題的文字描述
        
    Returns:
        舞蹈分析報告
    """
    return analyze_dance(user_input)
