Google Login + React/Chakra 外壳 — 实施规划（v1）
1. 架构方案图解（文字版）
浏览器访问前端 web/（Vite+React），静态资源经 Render CDN 或后端静态托管。
前端通过 fetch/axios withCredentials 调用后端 backend/（Flask+Authlib）API，域名建议 app.example.com（前端）与 api.example.com（后端），CORS 允许凭据。
用户点击登录→前端跳转 GET /api/auth/google/login→后端发起 Google OAuth2，成功后后端在同域或父域设置 httpOnly 会话 Cookie（SameSite=Lax，Secure），并 302 回 /app。
前端加载后调用 GET /api/me 校验登录，未登录时前端路由守卫跳转 /login。
旧 Jinja 模板继续由 Flask 渲染，部署期通过路径区分（如 /legacy/*）与新 React App 并行。
2. 实施分期计划（里程碑）
M1（后端优先）：配置 Google OAuth 凭证、实现 Authlib 登录流程、设置 Cookie 会话、/api/me 返回用户信息、完成最小回路自测。
M2（前端壳）：搭建 Vite+TS+React+Chakra、实现 /login 与 /app 路由、封装 Axios 实例支持凭据、加入基于 /api/me 的守卫和 Profile 视图。
M3（渐进迁移）：挑选 Name Generator 页，抽离后端数据接口、复用 API 逻辑、在 React 中实现与 Jinja 等价的 UI/交互。
M4（安全与观测）：接入速率限制/CSRF 保护、规范化登录失败和 401 响应、前端统一错误页、集中式日志与基础监控告警。
3. 关键技术决策与推荐
会话 Cookie：选用 Flask 服务端会话 + httpOnly + SameSite=Lax，简化凭据管理并兼容旧 Jinja。
UI 库：选 Chakra UI，组件轻量、主题定制自然，适合快速搭建 App Shell。
构建栈：采 Vite+React+TypeScript，拥有快速冷启动与类型安全。
HTTP 客户端：前端用 Axios withCredentials，统一处理 Cookie 凭据与错误态。
OAuth 库：使用 Authlib for Flask，官方维护、文档完善、与 Flask Session 集成顺滑。
4. 最小接口与路由列表（定义）
后端：GET /api/auth/google/login（触发 OAuth 重定向）；GET /api/auth/google/callback（校验 code、建立会话、302 /app）；POST /api/auth/logout（清理会话 Cookie）；GET /api/me（返回用户资料，未登录 401）。
前端路由：/login（渲染“Continue with Google”按钮，点击命中 /api/auth/google/login）；/app（App Shell 主页，守卫）；/app/profile（展示 /api/me 数据）；受保护路由高阶组件（拦截未登录用户）。
5. 目录与环境变量建议
目录结构：backend/（Flask 应用与 Jinja 仍在此）+ web/（Vite+React 项目）；共享 tools_config.py 等配置保留在根。
环境变量：GOOGLE_CLIENT_ID、GOOGLE_CLIENT_SECRET、GOOGLE_REDIRECT_URI、FRONTEND_URL、BACKEND_URL、SECRET_KEY，本地 .env 与 Render Secret 管理同步。
6. 本地与部署步骤
本地：1）在 backend/.env 写入 Google/Secret 配置；2）web/.env 设置 VITE_API_BASE_URL 与 FRONTEND_URL；3）先启 Flask（flask run 或 python app.py），后启 Vite；4）Vite 代理 /api 到 http://localhost:5000；5）浏览器访问 http://localhost:5173/login，完成登录自测。
部署选项：1）Render 双服务（Flask Web Service + Vite Static Site）；或 2）Flask 构建后端同时托管 web/dist；3）在 Google Console 配置授权 JS 来源（前端域）与重定向 URI（https://api.example.com/api/auth/google/callback）；4）同步更新 Render 环境变量；5）部署后验证 302 与 Cookie 域一致性。
7. 风险与回滚
OAuth redirect_uri 不匹配导致登录失败：保留旧登录路径以便回滚。
跨域凭据被浏览器拒绝：若出错可临时回退到旧 Jinja 登录页。
SameSite/Cookie 域配置不当：需预先验证子域策略，否则恢复旧认证逻辑。
速率限制或 CSRF 配置失误：上线前压测，出现异常时关闭 limiter 中间件回滚。
OAuth 时钟漂移：保证服务器时间同步，必要时暂时放宽 clock_skew.
8. 待确认问题
前后端最终是否同域或子域部署？
现有用户体系是否需要合并旧 session 或迁移？
是否存在移动端或桌面客户端需求？
当前数据库类型与用户表结构如何？
是否需要角色/权限（RBAC）控制？
Name Generator 页的 API 是否已模块化可复用？
旧 Jinja 页面计划保留多久、逐步迁移顺序？
是否需要审计登录日志或合规要求（如 GDPR）？