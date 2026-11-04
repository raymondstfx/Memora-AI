import re


def response_language(text: str, default: str) -> str:
    """Only explicit output-language instructions override the submitted locale."""
    if re.search(
        r"(?:\b(?:reply|answer|respond|write|generate)(?: \w+){0,3} in English\b|"
        r"English (?:summary|slides|presentation|email)|"
        r"用英文|用英语|使用英语|英文回答|英语回答|英文回复)",
        text,
        re.I,
    ):
        return "en"
    if re.search(
        r"(?:\b(?:reply|answer|respond|write|generate)(?: \w+){0,3} "
        r"in (?:Simplified )?Chinese\b|"
        r"Chinese (?:summary|slides|presentation|email)|用中文|使用中文|"
        r"中文(?:回答|摘要|简报|幻灯片|演示|邮件))",
        text,
        re.I,
    ):
        return "zh"
    return default


def language_instruction(language: str) -> str:
    return (
        (
            "\nWrite new response prose in Simplified Chinese. "
            if language == "zh"
            else "\nWrite new response prose in English. "
        )
        + "Preserve exact evidence quotes, names and "
        "identifiers. An explicit user output-language "
        "request takes priority."
    )
