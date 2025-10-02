Google Login + React/Chakra 外壳 — 实施规划（v1.1）
1. 架构方案图解（文字版）
浏览器访问同域站点（例如 https://app.example.com），前端 Vite+React+Chakra 的静态资源由 Render CDN 或 Flask 静态托管。
React 前端通过 axios withCredentials 调用同域下的 Flask API，避免跨域配置，仅需确保凭据透传。
登录流程：/login 触发 GET /api/auth/google/login → 后端用 Authlib 发起 OAuth → Google 回调 /api/auth/google/callback → 后端设置 httpOnly 会话 Cookie（SameSite=Lax，Secure）→ 302 回 /app。
React 初始化时调用 GET /api/me 校验会话；未登录跳转 /login。后续逐步将旧 Jinja 页面替换为 React 页面。
2. 实施分期计划（里程碑）
M1（OAuth 最小闭环）：配置 Authlib 与 Google 凭证、实现登录/回调/会话、/api/me 返回基本用户资料、自测登录流程。
M2（React App Shell）：搭建 Vite+TS+React+Chakra、实现 /login、/app、/app/profile、基于 /api/me 的守卫与导航框架。
M3（功能迁移）：为 Name Generator 抽取后端 API（若尚未独立）、在 React 中重写等效页面并与旧逻辑对齐、验证渐进迁移链路。
M4（安全与观测）：上线速率限制/CSRF 保护、统一错误与空状态页面、接入基础日志与健康探针，确保部署可观测。
3. 关键技术决策与推荐
会话 Cookie：沿用 Flask 服务端会话 + httpOnly + SameSite=Lax，与同域部署协同、兼容旧栈。
UI 框架：选用 Chakra UI，组件轻量、主题易定制，便于快速搭建 App Shell。
前端栈：Vite + React + TypeScript，开发体验快速、类型约束清晰。
HTTP 客户端：Axios withCredentials: true，统一处理同域 Cookie 与错误态。
OAuth 库：Authlib for Flask，集成简洁、支持 Google OAuth2/OIDC。
4. 最小接口与路由列表（定义）
后端：GET /api/auth/google/login（启动 OAuth）；GET /api/auth/google/callback（处理 code、建立会话、302 /app）；POST /api/auth/logout（清理会话）；GET /api/me（返回登录用户信息，未登录 401）。
前端：/login（“Continue with Google”按钮指向后端登录）；/app（App Shell 首页，受保护）；/app/profile（展示 /api/me 数据）；受保护路由组件（未登录自动重定向 /login）。
5. 目录与环境变量建议
目录：backend/（Flask 应用与旧 Jinja 模板）与 web/（Vite+React）并存；Root 下保留共享配置与脚本。
环境变量：GOOGLE_CLIENT_ID、GOOGLE_CLIENT_SECRET、GOOGLE_REDIRECT_URI、FRONTEND_URL、BACKEND_URL、SECRET_KEY；未来引入数据库时新增连接串。
6. 本地与部署步骤
本地：1）在 backend/.env 写入 Google/OAuth/Secret；2）web/.env 配置 VITE_API_BASE_URL 与 FRONTEND_URL; 3）启动 Flask（flask run 或 python app.py）；4）启动 Vite（默认 5173），配置代理指向 http://localhost:5000; 5）访问 /login 验证最小登录闭环。
部署：1）Render 上分别部署 Flask Web Service 与 React 静态站点，或由 Flask 托管编译后的 web/dist; 2）前后端同域（子路径或子域）配置；3）Google Console 设置授权 JS 来源/重定向 URI；4）Render 环境变量与 Secret 同步；5）部署后检查 Cookie、回调与 /api/me。
7. 风险与回滚
Google redirect_uri 不匹配：保留旧流程或临时禁用 OAuth，实现快速回退。
会话 Cookie 配置错误：提前在多浏览器验证 SameSite/Secure，必要时恢复旧登录。
Name Generator API 抽象不足：若 React 无法直接调用，先保持 Jinja 页面，待 API 抽离完成再切换。
速率限制或 CSRF 配置导致误封：上线前模拟高并发，必要时保留可切换的 feature flag。
OAuth 时钟偏差：保持服务器时间同步，出现问题可临时放宽 clock_skew。