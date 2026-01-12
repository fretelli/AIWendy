"""Backend i18n utilities (request-locale + translated strings).

This is intentionally lightweight: it resolves locale from request cookies/headers
and provides a simple key-based translation function.
"""

from __future__ import annotations

from typing import Any, Final, Literal, Mapping, Optional

from fastapi import Request

Locale = Literal["en", "zh"]

DEFAULT_LOCALE: Final[Locale] = "en"
LOCALE_COOKIE: Final[str] = "aiwendy-locale"
LEGACY_LOCALE_COOKIE: Final[str] = "aiwendy_lang"


def normalize_locale(value: Optional[str]) -> Locale:
    if not value:
        return DEFAULT_LOCALE
    v = value.strip().lower()
    if v.startswith("zh"):
        return "zh"
    return "en"


def get_request_locale(request: Request) -> Locale:
    cookie_locale = request.cookies.get(LOCALE_COOKIE) or request.cookies.get(
        LEGACY_LOCALE_COOKIE
    )
    if cookie_locale:
        return normalize_locale(cookie_locale)

    accept = request.headers.get("accept-language") or request.headers.get(
        "Accept-Language"
    )
    if accept:
        # e.g. "zh-CN,zh;q=0.9,en;q=0.8"
        first = accept.split(",")[0].strip()
        return normalize_locale(first)

    return DEFAULT_LOCALE


def join_names(names: list[str], locale: Locale) -> str:
    sep = "、" if locale == "zh" else ", "
    return sep.join([n for n in names if (n or "").strip()])


_MESSAGES: Final[Mapping[Locale, Mapping[str, str]]] = {
    "en": {
        "generic.coach": "Coach",
        "generic.moderator": "Moderator",
        "attachments.section": "Attachment contents",
        "attachments.file": "File",
        "attachments.audio_transcript": "Audio transcript",
        "attachments.image": "Image",
        "attachments.attachment": "Attachment",
        "kb.roundtable_intro": (
            "Reference context retrieved from the knowledge base (use only if relevant; do not fabricate citations):\n\n"
        ),
        "kb.chat_intro": (
            "Below are the most relevant snippets from the project knowledge base (for reference only).\n"
            "If irrelevant, ignore them; if relevant, prioritize them when answering:\n\n"
        ),
        "projects.default.name": "Default Project",
        "projects.default.description": "Automatically created default project",
        "roundtable.title_default": "Roundtable - {ts}",
        "roundtable.system_context": (
            "\n\n"
            "You are participating in a roundtable discussion about trading psychology.\n"
            "Participants: {participants}\n"
            "Your role: {coach_name} ({coach_style} style).\n\n"
            "Rules:\n"
            "1. Keep your unique personality and communication style\n"
            "2. You may respond to, add to, or respectfully challenge other coaches' viewpoints\n"
            "3. Keep each turn concise (2-4 sentences)\n"
            "4. Focus on the user's concrete question and give high-value advice\n"
            "5. If other coaches already gave good suggestions, add rather than repeat\n\n"
            "Other coaches: {other_coaches}\n"
        ),
        "roundtable.debate.round1": (
            "Round 1: give your core judgment and advice from your own style.\n"
            "Requirements: 2-4 sentences; be concrete and actionable; do not restate others (debate hasn't started yet)."
        ),
        "roundtable.debate.clash": (
            "Debate round {round_num} (clash style): you MUST cite at least one other coach by name,\n"
            "point out potential risks/blind spots (you may disagree), then provide your alternative or stricter boundaries.\n"
            "Finally, output 1 key actionable step.\n"
            "Requirements: 2-5 sentences; avoid repeating yourself from last round; stay professional but allow constructive pushback."
        ),
        "roundtable.debate.converge": (
            "Debate round {round_num} (converge & refine): you MUST cite at least one other coach by name,\n"
            "state what you agree with / add / correct, and merge viewpoints into a clearer execution plan (priority and conditions).\n"
            "Finally, output 1-2 more concrete, actionable suggestions.\n"
            "Requirements: 2-5 sentences; avoid repeating yourself from last round; stay professional and execution-focused."
        ),
        "roundtable.moderator.opening": (
            "\n\n"
            "You are the moderator of this roundtable discussion.\n"
            "Coaches: {coach_styles}\n"
            "User question: {user_question}\n\n"
            "Open in 2-3 sentences:\n"
            "1) Briefly frame what kind of problem this is\n"
            "2) Preview which coaches will analyze from which angles\n\n"
            "Notes:\n"
            "- Keep it concise and professional\n"
            "- Do not repeat the user's question verbatim\n"
            "- Tell the user what will happen next\n"
        ),
        "roundtable.moderator.summary": (
            "\n\n"
            "You are the moderator. Summarize this round.\n\n"
            "Coaches' viewpoints:\n"
            "{messages}\n\n"
            "In 3-4 sentences:\n"
            "1) Summarize each coach's key points and advice\n"
            "2) Highlight consensus and disagreements (if any)\n"
            "3) Ask one deepening question for the user to consider or follow up\n\n"
            "Notes:\n"
            "- Stay neutral and objective\n"
            "- Focus on key points; do not repeat everything\n"
            "- The deepening question should be insightful\n"
        ),
        "roundtable.moderator.closing": (
            "\n\n"
            "You are the moderator. The discussion is ending; give a closing.\n\n"
            "Discussion overview:\n"
            "{contrib}\n\n"
            "In 4-5 sentences:\n"
            "1) Thank the coaches\n"
            "2) Synthesize 2-3 core recommendations\n"
            "3) Encourage the user to put them into practice\n"
            "4) Invite the user to start a new discussion anytime\n\n"
            "Notes:\n"
            "- Make it integrative (not just a list)\n"
            "- Keep recommendations concrete and actionable\n"
            "- Keep a warm, professional tone\n"
        ),
        "roundtable.fallback.opening": "Welcome to this roundtable. Let’s invite each coach to share their perspective on your question.",
        "roundtable.fallback.summary": "Thanks to all coaches. Let’s continue exploring this topic with the key points in mind.",
        "roundtable.fallback.closing": "Thanks to all coaches and for your participation. Hope this discussion helps—feel free to start a new one anytime!",
        "roundtable.fallback.coach_error": "Sorry, I can't respond right now. Please try again later.",
        "errors.preset_not_found": "Preset not found",
        "errors.preset_or_coaches_required": "Either preset_id or coach_ids is required",
        "errors.session_not_found": "Session not found",
        "errors.access_denied": "Access denied",
        "errors.session_not_active": "Session is not active",
        "errors.no_valid_coaches": "No valid coaches in session",
        "errors.some_coaches_not_found": "Some coaches not found",
        "errors.min_coaches": "At least 2 coaches are required",
        "errors.max_coaches": "Maximum 5 coaches allowed",
        "errors.moderator_not_found": "Moderator not found",
        "errors.moderator_not_found_with_id": "Moderator '{moderator_id}' not found",
        "errors.llm_config_not_found": "LLM config not found",
        "errors.llm_config_inactive": "LLM config is not active",
        "errors.no_llm_provider": "No LLM provider configured. Please set up API keys.",
        "errors.no_llm_providers_configured": "No LLM providers configured. Please configure one in Settings → LLM Configuration.",
        "errors.chat_session_not_found": "Chat session not found",
        "errors.chat_coach_mismatch": "coach_id does not match the chat session coach",
        "errors.llm_configuration_not_found": "LLM configuration not found",
        "errors.llm_configuration_inactive": "LLM configuration is not active",
        "errors.llm_configuration_use_failed": "Failed to use selected LLM configuration: {detail}",
        "errors.project_name_required": "Project name is required",
        "errors.project_name_exists": "Project name already exists",
        "errors.project_not_found": "Project not found",
        "errors.project_name_cannot_be_empty": "Project name cannot be empty",
        "messages.session_ended": "Session ended",
        "errors.internal": "An internal error occurred",
        "errors.rate_limit_exceeded": "Rate limit of {limit} per {window}s exceeded",
        "errors.authentication_failed": "Authentication failed",
        "errors.invalid_credentials": "Invalid email or password",
        "errors.token_expired": "Token has expired",
        "errors.invalid_token": "Invalid token",
        "errors.not_authorized": "Not authorized",
        "errors.validation_failed": "Validation failed for field '{field}': {error}",
        "errors.duplicate_resource": "{resource} with {field} '{value}' already exists",
        "errors.filename_required": "Filename is required",
        "errors.file_too_large": "File too large. Maximum size for {file_category} files is {max_mb}MB",
        "errors.invalid_image_file": "Invalid image file",
        "errors.cannot_extract_text_from_category": "Cannot extract text from {file_category} files",
        "errors.failed_to_process_file": "Failed to process file",
        "errors.only_audio_supported_for_transcription": "Only audio files are supported for transcription",
        "errors.audio_file_too_large": "Audio file too large. Maximum size is {max_mb}MB",
        "errors.openai_api_key_not_configured": "OpenAI API key not configured. Cannot transcribe audio.",
        "errors.transcription_failed": "Transcription failed",
        "errors.file_not_found": "File not found",
        "errors.file_not_found_or_deleted": "File not found or already deleted",
        "messages.file_deleted": "File deleted",
        "errors.title_and_content_required": "Title and content are required",
        "errors.content_empty_after_cleaning": "Content is empty after cleaning",
        "errors.no_embedding_provider": "No embedding provider available (configure OpenAI, Ollama, or a custom API with embedding support)",
        "errors.failed_generate_embeddings": "Failed to generate embeddings",
        "errors.document_not_found": "Document not found",
        "errors.query_required": "q is required",
        "errors.invalid_openai_api_key_format": "Invalid OpenAI API key format. Must start with 'sk-'",
        "errors.invalid_anthropic_api_key_format": "Invalid Anthropic API key format. Must start with 'sk-ant-'",
        "messages.api_keys_updated": "API keys updated successfully",
        "errors.failed_update_api_keys": "Failed to update API keys",
        "errors.unknown_api_key_provider": "Unknown provider: {provider}. Supported: openai, anthropic",
        "messages.api_key_deleted": "Deleted {provider} API key successfully",
        "errors.no_default_coach_configured": "No default coach configured",
        "errors.coach_not_found": "Coach not found",
        "errors.failed_allocate_coach_id": "Failed to allocate coach id",
        "chat.session_title_default": "Chat - {ts}",
        "chat.language_instruction": "Always respond in English.",
        "errors.failed_to_retrieve_messages": "Failed to retrieve messages",
        "errors.failed_to_create_journal_entry": "Failed to create journal entry",
        "errors.failed_to_list_journal_entries": "Failed to list journal entries",
        "errors.failed_to_get_journal_statistics": "Failed to get statistics",
        "errors.invalid_mapping_json": "Invalid mapping_json: {error}",
        "errors.mapping_missing_symbol_direction": "Mapping must include 'symbol' and 'direction'",
        "messages.import_row_error": "Row {row}: {error}",
        "errors.failed_to_import_journal_entries": "Failed to import journal entries",
        "errors.journal_entry_not_found": "Journal entry not found",
        "errors.failed_to_get_journal_entry": "Failed to get journal entry",
        "errors.failed_to_update_journal_entry": "Failed to update journal entry",
        "messages.journal_entry_deleted": "Journal entry deleted successfully",
        "errors.failed_to_delete_journal_entry": "Failed to delete journal entry",
        "errors.failed_to_create_quick_journal_entry": "Failed to create quick journal entry",
        "errors.failed_to_analyze_journal_entry": "Failed to analyze journal entry",
        "errors.failed_to_analyze_trading_patterns": "Failed to analyze trading patterns",
        "errors.failed_to_generate_improvement_plan": "Failed to generate improvement plan",
        "messages.no_journal_entries_for_analysis": "No journal entries found for analysis",
        "messages.not_enough_data_for_improvement_plan": "Not enough data to generate improvement plan",
        "messages.improvement_plan_start_journaling": "Start journaling your trades consistently for at least 10 trades to get a personalized improvement plan.",
        "errors.unsupported_report_type": "Unsupported report type",
        "errors.report_generation_failed": "Report could not be generated",
        "errors.no_report_found_for_user": "No {report_type} report found for user",
        "errors.report_not_found": "Report not found",
        "errors.market_data_not_found": "No data found for symbol {symbol}",
        "errors.invalid_date_format": "Invalid date format: {error}",
        "errors.market_data_fetch_failed": "Error fetching market data",
        "errors.invalid_indicator": "Invalid indicator. Must be one of: {valid}",
        "errors.market_indicator_data_not_found": "No indicator data found for symbol {symbol}",
        "errors.market_indicators_failed": "Error calculating indicators",
        "errors.market_symbol_search_failed": "Error searching symbols",
        "messages.task_waiting": "Task is waiting to be processed",
        "messages.task_started": "Task has started processing",
        "messages.daily_report_queued": "Daily report generation has been queued",
        "messages.weekly_report_queued": "Weekly report generation has been queued",
        "messages.monthly_report_queued": "Monthly report generation has been queued",
        "messages.knowledge_ingestion_queued": "Knowledge ingestion has been queued",
        "messages.semantic_search_queued": "Semantic search has been queued",
        "errors.admin_access_required": "Admin access required",
        "errors.task_already_completed": "Task {task_id} has already completed",
        "messages.task_cancelled": "Task has been cancelled",
        "errors.no_model_specified": "No model specified. Please set a default model or fetch models first.",
        "errors.no_llm_configurations_found": "No configurations found",
        "errors.base_url_required_for_custom_provider": "base_url is required for custom provider",
        "errors.fetch_models_failed": "Failed to fetch models: {detail}",
        "messages.llm_configuration_created": "LLM configuration created successfully",
        "messages.llm_configuration_updated": "Configuration updated successfully",
        "messages.llm_configuration_deleted": "Configuration deleted successfully",
        "errors.failed_to_decrypt_api_key": "Failed to decrypt API key",
        "errors.request_timed_out": "Request timed out after {seconds} seconds",
        "errors.llm_test_failed": "Test failed: {detail}",
        "llm_test.system_prompt": "You are a helpful AI assistant. Keep your response brief and friendly.",
        "errors.connection_timed_out": "Connection timeout ({seconds}s)",
        "messages.ollama_service_running": "Ollama service is running",
        "errors.ollama_not_available": "Ollama service is not available",
        "errors.ollama_model_not_available": "Model {model} is not available. Please pull it first.",
        "ollama.test_chat_system_prompt": "You are a trading psychology coach. Provide helpful and concise responses.",
        "coaches.wendy.name": "Wendy Rhodes",
        "coaches.wendy.description": "Empathetic coach focused on emotional regulation and mental resilience",
        "coaches.wendy.bio": "Wendy is a seasoned trading psychology coach who helps traders navigate emotional swings and overcome fear and greed.",
        "coaches.marcus.name": "Marcus Steel",
        "coaches.marcus.description": "Disciplined coach emphasizing risk control and execution",
        "coaches.marcus.bio": "A former hedge fund manager, Marcus now focuses on training trading discipline and accountability.",
        "coaches.sophia.name": "Dr. Sophia Chen",
        "coaches.sophia.description": "Analytical coach using data-driven decision making",
        "coaches.sophia.bio": "With a PhD in Financial Engineering, Sophia specializes in quantitative analysis and performance optimization.",
        "coaches.alex.name": "Alex Thunder",
        "coaches.alex.description": "Motivational coach who ignites confidence and drive",
        "coaches.alex.bio": "A high-energy coach who helps traders rebuild confidence, stay motivated, and take consistent action.",
        "coaches.socrates.name": "Socrates",
        "coaches.socrates.description": "Socratic coach guiding self-discovery through questions",
        "coaches.socrates.bio": "Named after the Greek philosopher, this coach uses Socratic questioning to surface assumptions and sharpen thinking.",
        "reports.type.daily": "daily",
        "reports.type.weekly": "weekly",
        "reports.type.monthly": "monthly",
        "reports.title.daily": "Trading Daily Report - {date}",
        "reports.title.weekly": "Trading Weekly Report - Week {week}",
        "reports.title.monthly": "Trading Monthly Report - {month_label}",
        "reports.title.with_project": "{title} ({project})",
        "reports.subtitle.period": "{start} to {end}",
        "reports.mood.1": "Very tense",
        "reports.mood.2": "Tense",
        "reports.mood.3": "Neutral",
        "reports.mood.4": "Calm",
        "reports.mood.5": "Very calm",
        "reports.improvement.early_exit": "Early exit: pre-define take-profit/stop-loss rules and follow them strictly",
        "reports.improvement.late_exit": "Late stop/TP: use conditional orders or reminders to avoid hesitation",
        "reports.improvement.no_stop_loss": "No stop-loss: define risk before every trade",
        "reports.improvement.over_leverage": "Over leverage: reduce leverage/position size; prioritize survival",
        "reports.improvement.revenge_trade": "Revenge trading: enforce a cooldown after losses to avoid emotional decisions",
        "reports.improvement.fomo": "FOMO: only take setups that meet your system rules; avoid chasing",
        "reports.improvement.position_size": "Position too large: size positions using a fixed-risk model",
        "reports.improvement.other": "Other: write down triggers and create targeted rules",
        "reports.improvement.generic": "Reduce the frequency of {key}",
        "reports.improvement.with_frequency": "{tip} (current: {count})",
        "reports.ai.no_trades": "No trades recorded for this period.",
        "reports.ai.system_prompt": "You are a professional trading psychology coach. Provide concise, concrete, actionable feedback. Respond in English.",
        "reports.ai.prompt": (
            "Analyze the following {report_type} trading report data.\n\n"
            "Statistics:\n"
            "- Total trades: {total_trades}\n"
            "- Win rate: {win_rate}%\n"
            "- Total PnL: {total_pnl}\n"
            "- Average PnL: {avg_pnl}\n\n"
            "Psychology:\n"
            "- Average mood before: {avg_mood_before}\n"
            "- Average mood after: {avg_mood_after}\n"
            "- Mood change: {mood_improvement}\n\n"
            "Provide:\n"
            "1) Deep analysis (<= 200 words)\n"
            "2) 3 key insights\n"
            "3) 3 concrete improvement suggestions\n"
            "4) 3 actionable action items\n\n"
            "Return JSON with keys: analysis, key_insights, recommendations, action_items.\n"
            "Respond in English."
        ),
        "reports.fallback.analysis_header": "This period you completed {total_trades} trades, win rate {win_rate}%. ",
        "reports.fallback.analysis_profit": "Overall profit {total_pnl}. ",
        "reports.fallback.analysis_loss": "Overall loss {total_loss}. ",
        "reports.fallback.rec.low_win_rate": "Raise your entry criteria to reduce low-quality trades.",
        "reports.fallback.rec.mood_negative": "Watch the negative emotional impact of trading; consider smaller size or lower frequency.",
        "reports.fallback.rec.top_mistake": "Focus on fixing the most common mistake: {mistake}.",
        "reports.fallback.insight.system_good": "Your trading system performance is solid—keep following the current process.",
        "reports.fallback.insight.risk_good": "Risk control looks good; stop-loss execution appears disciplined.",
        "reports.fallback.insight.mood_positive": "Trading appears to have a positive impact on your mental state.",
        "reports.fallback.action.review_max_loss": "Review your biggest losing trade this period and extract the lesson.",
        "reports.fallback.action.analyze_best_trade": "Analyze your best trade and distill a repeatable pattern.",
        "reports.fallback.action.plan_next_period": "Create a plan and risk rules for the next period.",
        "reports.coach.notes": "{count} coaching sessions",
        "reports.summary.period": "{start} to {end}",
        "reports.summary.base": "During {period}, you completed {total_trades} trades. ",
        "reports.summary.win_rate": "Win rate: {win_rate}%. ",
        "reports.summary.profit": "Total profit: {total_pnl:.2f}. ",
        "reports.summary.loss": "Total loss: {total_loss:.2f}. ",
        "reports.summary.mood_improved": "Mood improved after trading.",
        "reports.summary.mood_worsened": "Mood worsened after trading.",
    },
    "zh": {
        "generic.coach": "教练",
        "generic.moderator": "主持人",
        "attachments.section": "附件内容",
        "attachments.file": "文件",
        "attachments.audio_transcript": "语音转写",
        "attachments.image": "图片",
        "attachments.attachment": "附件",
        "kb.roundtable_intro": "以下为知识库检索到的参考内容（仅在相关时使用，不要编造引用）：\n\n",
        "kb.chat_intro": (
            "以下是与当前问题最相关的「项目知识库」片段（仅供参考）。\n"
            "如果与问题无关，请忽略；如果相关，请优先依据这些内容作答：\n\n"
        ),
        "projects.default.name": "默认项目",
        "projects.default.description": "系统自动创建的默认项目",
        "roundtable.title_default": "圆桌讨论 - {ts}",
        "roundtable.system_context": (
            "\n\n"
            "你正在参与一场关于交易心理的圆桌讨论。\n"
            "参与者：{participants}\n"
            "你的角色是 {coach_name}（{coach_style}风格）。\n\n"
            "讨论规则：\n"
            "1. 保持你独特的个性和沟通风格\n"
            "2. 可以回应、补充或友好地质疑其他教练的观点\n"
            "3. 每次发言保持简洁，2-4 句话即可\n"
            "4. 关注用户的具体问题，给出有价值的建议\n"
            "5. 如果其他教练已经给出了好的建议，可以补充而不是重复\n\n"
            "其他教练：{other_coaches}\n"
        ),
        "roundtable.debate.round1": (
            "你正在进行第 1 轮讨论：请给出你从自己风格出发的核心判断与建议。\n"
            "要求：2-4 句，尽量具体可执行；不要复述其他人（因为还没开始互辩）。"
        ),
        "roundtable.debate.clash": (
            "你正在进行第 {round_num} 轮互辩（对立辩论风格）：你必须点名引用至少 1 位其他教练的观点，\n"
            "并指出其建议的潜在风险/盲点（可以不同意），然后给出你的替代方案或更严格的边界条件。\n"
            "最后输出 1 条你认为最关键、最可执行的动作建议。\n"
            "要求：2-5 句；避免重复上一轮自己的话；保持专业但允许有建设性的反驳。"
        ),
        "roundtable.debate.converge": (
            "你正在进行第 {round_num} 轮互辩（收敛纠错风格）：你必须点名引用至少 1 位其他教练的观点，\n"
            "说明你同意/补充/纠错的点，并把各方观点合并成更清晰的执行方案（明确优先级或适用条件）。\n"
            "最后输出 1-2 条更具体、可执行的建议。\n"
            "要求：2-5 句；避免重复上一轮自己的话；保持专业、聚焦可执行。"
        ),
        "roundtable.moderator.opening": (
            "\n\n"
            "你是本次圆桌讨论的主持人。\n"
            "参与教练：{coach_styles}\n"
            "用户问题：{user_question}\n\n"
            "请用 2-3 句话开场：\n"
            "1. 简要破题，说明这是个什么类型的问题\n"
            "2. 预告将邀请哪些教练从哪些角度来分析这个问题\n\n"
            "注意：\n"
            "- 保持简洁专业\n"
            "- 不要重复用户的问题原文\n"
            "- 让用户知道接下来会发生什么\n"
        ),
        "roundtable.moderator.summary": (
            "\n\n"
            "你是主持人，请总结本轮讨论。\n\n"
            "各教练观点：\n"
            "{messages}\n\n"
            "请用 3-4 句话：\n"
            "1. 总结各教练的核心观点和建议\n"
            "2. 指出他们观点中的共识和分歧（如果有）\n"
            "3. 提出一个深化问题供用户思考或追问\n\n"
            "注意：\n"
            "- 保持中立客观\n"
            "- 突出要点，不要重复全部内容\n"
            "- 深化问题要有启发性\n"
        ),
        "roundtable.moderator.closing": (
            "\n\n"
            "你是主持人，讨论即将结束，请给出结语。\n\n"
            "讨论概况：\n"
            "{contrib}\n\n"
            "请用 4-5 句话：\n"
            "1. 感谢各位教练的精彩分享\n"
            "2. 综合各教练观点，给出 2-3 条核心建议\n"
            "3. 鼓励用户将建议付诸实践\n"
            "4. 欢迎用户随时开启新的讨论\n\n"
            "注意：\n"
            "- 总结要有综合性，不是简单罗列\n"
            "- 建议要具体可执行\n"
            "- 语气温和专业\n"
        ),
        "roundtable.fallback.opening": "欢迎来到本次圆桌讨论。让我们请各位教练就这个问题分享自己的见解。",
        "roundtable.fallback.summary": "感谢各位教练的精彩分享。让我们继续深入探讨这个问题。",
        "roundtable.fallback.closing": "感谢各位教练的精彩分享和用户的积极参与。希望今天的讨论对您有所帮助，欢迎随时开启新的讨论！",
        "roundtable.fallback.coach_error": "抱歉，我暂时无法回应。请稍后再试。",
        "errors.preset_not_found": "预设不存在",
        "errors.preset_or_coaches_required": "preset_id 或 coach_ids 必须提供其一",
        "errors.session_not_found": "会话不存在",
        "errors.access_denied": "无权限",
        "errors.session_not_active": "会话未激活或已结束",
        "errors.no_valid_coaches": "会话中没有可用教练",
        "errors.some_coaches_not_found": "部分教练不存在",
        "errors.min_coaches": "至少需要 2 位教练",
        "errors.max_coaches": "最多只能选择 5 位教练",
        "errors.moderator_not_found": "主持人不存在",
        "errors.moderator_not_found_with_id": "主持人 '{moderator_id}' 不存在",
        "errors.llm_config_not_found": "LLM 配置不存在",
        "errors.llm_config_inactive": "LLM 配置已停用",
        "errors.no_llm_provider": "未配置 LLM 提供商，请先设置 API Key。",
        "errors.no_llm_providers_configured": "未配置任何 LLM 提供商，请在「设置 → LLM 配置」中完成配置。",
        "errors.chat_session_not_found": "聊天会话不存在",
        "errors.chat_coach_mismatch": "coach_id 与会话中的教练不匹配",
        "errors.llm_configuration_not_found": "LLM 配置不存在",
        "errors.llm_configuration_inactive": "LLM 配置已停用",
        "errors.llm_configuration_use_failed": "无法使用所选 LLM 配置：{detail}",
        "errors.project_name_required": "项目名称不能为空",
        "errors.project_name_exists": "项目名称已存在",
        "errors.project_not_found": "项目不存在",
        "errors.project_name_cannot_be_empty": "项目名称不能为空",
        "messages.session_ended": "会话已结束",
        "errors.internal": "服务器内部错误",
        "errors.rate_limit_exceeded": "请求过于频繁：每 {window} 秒最多 {limit} 次",
        "errors.authentication_failed": "认证失败",
        "errors.invalid_credentials": "邮箱或密码错误",
        "errors.token_expired": "令牌已过期",
        "errors.invalid_token": "无效的令牌",
        "errors.not_authorized": "无权限",
        "errors.validation_failed": "字段“{field}”校验失败：{error}",
        "errors.duplicate_resource": "{resource} 的 {field}“{value}”已存在",
        "errors.filename_required": "文件名不能为空",
        "errors.file_too_large": "文件过大：{file_category} 文件最大 {max_mb}MB",
        "errors.invalid_image_file": "无效的图片文件",
        "errors.cannot_extract_text_from_category": "无法从 {file_category} 文件中提取文本",
        "errors.failed_to_process_file": "文件处理失败",
        "errors.only_audio_supported_for_transcription": "仅支持音频文件转写",
        "errors.audio_file_too_large": "音频文件过大：最大 {max_mb}MB",
        "errors.openai_api_key_not_configured": "未配置 OpenAI API Key，无法转写音频。",
        "errors.transcription_failed": "音频转写失败",
        "errors.file_not_found": "文件不存在",
        "errors.file_not_found_or_deleted": "文件不存在或已删除",
        "messages.file_deleted": "文件已删除",
        "errors.title_and_content_required": "标题和内容不能为空",
        "errors.content_empty_after_cleaning": "清洗后内容为空",
        "errors.no_embedding_provider": "没有可用的 embedding 提供方（请配置 OpenAI、Ollama 或支持 embedding 的自定义 API）",
        "errors.failed_generate_embeddings": "生成向量失败",
        "errors.document_not_found": "文档不存在",
        "errors.query_required": "q 不能为空",
        "errors.invalid_openai_api_key_format": "OpenAI API Key 格式无效，必须以“sk-”开头",
        "errors.invalid_anthropic_api_key_format": "Anthropic API Key 格式无效，必须以“sk-ant-”开头",
        "messages.api_keys_updated": "API Key 更新成功",
        "errors.failed_update_api_keys": "更新 API Key 失败",
        "errors.unknown_api_key_provider": "未知的 provider：{provider}。支持：openai、anthropic",
        "messages.api_key_deleted": "已删除 {provider} API Key",
        "errors.no_default_coach_configured": "未配置默认教练",
        "errors.coach_not_found": "教练不存在",
        "errors.failed_allocate_coach_id": "分配教练 ID 失败",
        "chat.session_title_default": "对话 - {ts}",
        "chat.language_instruction": "请始终用简体中文回答。",
        "errors.failed_to_retrieve_messages": "获取消息失败",
        "errors.failed_to_create_journal_entry": "创建交易日志失败",
        "errors.failed_to_list_journal_entries": "获取交易日志列表失败",
        "errors.failed_to_get_journal_statistics": "获取统计数据失败",
        "errors.invalid_mapping_json": "mapping_json 无效：{error}",
        "errors.mapping_missing_symbol_direction": "映射必须包含“symbol”和“direction”",
        "messages.import_row_error": "第 {row} 行：{error}",
        "errors.failed_to_import_journal_entries": "导入交易日志失败",
        "errors.journal_entry_not_found": "交易日志不存在",
        "errors.failed_to_get_journal_entry": "获取交易日志失败",
        "errors.failed_to_update_journal_entry": "更新交易日志失败",
        "messages.journal_entry_deleted": "交易日志已删除",
        "errors.failed_to_delete_journal_entry": "删除交易日志失败",
        "errors.failed_to_create_quick_journal_entry": "创建快速交易日志失败",
        "errors.failed_to_analyze_journal_entry": "分析交易日志失败",
        "errors.failed_to_analyze_trading_patterns": "分析交易模式失败",
        "errors.failed_to_generate_improvement_plan": "生成改进计划失败",
        "messages.no_journal_entries_for_analysis": "没有可用于分析的交易日志",
        "messages.not_enough_data_for_improvement_plan": "数据不足，无法生成改进计划",
        "messages.improvement_plan_start_journaling": "请至少连续记录 10 笔交易日志，以生成个性化改进计划。",
        "errors.unsupported_report_type": "不支持的报告类型",
        "errors.report_generation_failed": "报告生成失败",
        "errors.no_report_found_for_user": "未找到用户的 {report_type} 报告",
        "errors.report_not_found": "报告不存在",
        "errors.market_data_not_found": "未找到 {symbol} 的数据",
        "errors.invalid_date_format": "日期格式无效：{error}",
        "errors.market_data_fetch_failed": "获取行情数据失败",
        "errors.invalid_indicator": "指标无效，必须是以下之一：{valid}",
        "errors.market_indicator_data_not_found": "未找到 {symbol} 的指标数据",
        "errors.market_indicators_failed": "计算指标失败",
        "errors.market_symbol_search_failed": "搜索代码失败",
        "messages.task_waiting": "任务排队中",
        "messages.task_started": "任务处理中",
        "messages.daily_report_queued": "已加入日报生成队列",
        "messages.weekly_report_queued": "已加入周报生成队列",
        "messages.monthly_report_queued": "已加入月报生成队列",
        "messages.knowledge_ingestion_queued": "已加入知识库导入队列",
        "messages.semantic_search_queued": "已加入语义搜索队列",
        "errors.admin_access_required": "需要管理员权限",
        "errors.task_already_completed": "任务 {task_id} 已完成",
        "messages.task_cancelled": "任务已取消",
        "errors.no_model_specified": "未指定模型，请先设置默认模型或先获取模型列表",
        "errors.no_llm_configurations_found": "未找到配置",
        "errors.base_url_required_for_custom_provider": "自定义提供方必须填写 base_url",
        "errors.fetch_models_failed": "获取模型列表失败：{detail}",
        "messages.llm_configuration_created": "LLM 配置创建成功",
        "messages.llm_configuration_updated": "配置更新成功",
        "messages.llm_configuration_deleted": "配置删除成功",
        "errors.failed_to_decrypt_api_key": "解密 API Key 失败",
        "errors.request_timed_out": "请求超时（{seconds} 秒）",
        "errors.llm_test_failed": "测试失败：{detail}",
        "llm_test.system_prompt": "你是一个有帮助的 AI 助手。请保持回答简洁友好。",
        "errors.connection_timed_out": "连接超时（{seconds} 秒）",
        "messages.ollama_service_running": "Ollama 服务运行正常",
        "errors.ollama_not_available": "Ollama 服务不可用",
        "errors.ollama_model_not_available": "模型 {model} 不可用，请先拉取（pull）",
        "ollama.test_chat_system_prompt": "你是一名交易心理教练，请提供有帮助且简洁的回答。",
        "coaches.wendy.name": "Wendy Rhodes",
        "coaches.wendy.description": "温和共情型教练，专注于情绪管理和心理韧性",
        "coaches.wendy.bio": "Wendy 是一位资深交易心理教练，擅长帮助交易者处理情绪波动、克服恐惧与贪婪。",
        "coaches.marcus.name": "Marcus Steel",
        "coaches.marcus.description": "严厉纪律型教练，强调风控和执行力",
        "coaches.marcus.bio": "Marcus Steel 是一位前对冲基金经理，现专注于交易纪律培训。",
        "coaches.sophia.name": "Dr. Sophia Chen",
        "coaches.sophia.description": "数据分析型教练，用数据驱动决策",
        "coaches.sophia.bio": "Dr. Sophia Chen 拥有金融工程博士学位，专注于量化分析和数据驱动的交易改进。",
        "coaches.alex.name": "Alex Thunder",
        "coaches.alex.description": "激励鼓舞型教练，激发潜能和斗志",
        "coaches.alex.bio": "Alex Thunder 是一位充满激情的励志教练，曾帮助数百位交易者重燃斗志。",
        "coaches.socrates.name": "Socrates",
        "coaches.socrates.description": "苏格拉底式教练，通过提问引导自我发现",
        "coaches.socrates.bio": "以古希腊哲学家苏格拉底命名，这位教练采用经典的苏格拉底式提问法。",
        "reports.type.daily": "日报",
        "reports.type.weekly": "周报",
        "reports.type.monthly": "月报",
        "reports.title.daily": "交易日报 - {date}",
        "reports.title.weekly": "交易周报 - 第{week}周",
        "reports.title.monthly": "交易月报 - {month_label}",
        "reports.title.with_project": "{title}（{project}）",
        "reports.subtitle.period": "{start} 至 {end}",
        "reports.mood.1": "很紧张",
        "reports.mood.2": "紧张",
        "reports.mood.3": "一般",
        "reports.mood.4": "平静",
        "reports.mood.5": "很平静",
        "reports.improvement.early_exit": "提前退出：提前制定止盈/止损规则并严格执行",
        "reports.improvement.late_exit": "晚止损/止盈：设置条件单或提醒，避免犹豫",
        "reports.improvement.no_stop_loss": "未设止损：每笔交易必须先定义风险",
        "reports.improvement.over_leverage": "杠杆过高：降低杠杆与仓位，优先保证生存",
        "reports.improvement.revenge_trade": "报复性交易：亏损后强制冷静期，避免情绪决策",
        "reports.improvement.fomo": "FOMO：只做符合系统条件的机会，避免追涨杀跌",
        "reports.improvement.position_size": "仓位过大：用固定风险模型计算仓位",
        "reports.improvement.other": "其他：记录触发场景，针对性制定规则",
        "reports.improvement.generic": "减少 {key} 的发生频率",
        "reports.improvement.with_frequency": "{tip}（当前：{count} 次）",
        "reports.ai.no_trades": "本期无交易记录。",
        "reports.ai.system_prompt": "你是一位专业的交易心理教练，擅长总结交易表现、识别行为模式并给出改进建议。请用简体中文回答。",
        "reports.ai.prompt": (
            "作为专业的交易心理教练，请分析以下{report_type}交易报告数据：\n\n"
            "统计数据：\n"
            "- 总交易次数：{total_trades}\n"
            "- 胜率：{win_rate}%\n"
            "- 总盈亏：{total_pnl}\n"
            "- 平均盈亏：{avg_pnl}\n\n"
            "心理指标：\n"
            "- 交易前平均情绪：{avg_mood_before}\n"
            "- 交易后平均情绪：{avg_mood_after}\n"
            "- 情绪改善：{mood_improvement}\n\n"
            "请提供：\n"
            "1）深度分析（200字以内）\n"
            "2）3个关键洞察\n"
            "3）3个具体的改进建议\n"
            "4）3个可执行的行动项\n\n"
            "请用 JSON 格式返回，包含键：analysis、key_insights、recommendations、action_items。"
        ),
        "reports.fallback.analysis_header": "本期共完成{total_trades}笔交易，胜率{win_rate}%，",
        "reports.fallback.analysis_profit": "总体盈利{total_pnl}。",
        "reports.fallback.analysis_loss": "总体亏损{total_loss}。",
        "reports.fallback.rec.low_win_rate": "提高选择交易机会的标准，减少低质量交易",
        "reports.fallback.rec.mood_negative": "关注交易对情绪的负面影响，考虑减小仓位或降低频率",
        "reports.fallback.rec.top_mistake": "重点解决最常见的错误：{mistake}",
        "reports.fallback.insight.system_good": "交易系统表现良好，保持当前策略",
        "reports.fallback.insight.risk_good": "风险控制得当，止损执行良好",
        "reports.fallback.insight.mood_positive": "交易过程对心理状态有积极影响",
        "reports.fallback.action.review_max_loss": "回顾本期最大亏损交易，总结教训",
        "reports.fallback.action.analyze_best_trade": "分析最成功的交易，提炼可复制模式",
        "reports.fallback.action.plan_next_period": "制定下期交易计划和风险管理规则",
        "reports.coach.notes": "共进行了{count}次对话",
        "reports.summary.period": "{start}至{end}",
        "reports.summary.base": "在{period}期间，您共完成{total_trades}笔交易。",
        "reports.summary.win_rate": "胜率为{win_rate}%，",
        "reports.summary.profit": "总体盈利{total_pnl:.2f}。",
        "reports.summary.loss": "总体亏损{total_loss:.2f}。",
        "reports.summary.mood_improved": "交易后情绪有所改善。",
        "reports.summary.mood_worsened": "需要关注交易对情绪的影响。",
    },
}


def t(key: str, locale: Locale, **params: Any) -> str:
    table = _MESSAGES.get(locale) or _MESSAGES[DEFAULT_LOCALE]
    template = table.get(key) or _MESSAGES[DEFAULT_LOCALE].get(key) or key
    try:
        return template.format(**params)
    except Exception:
        return template
