# 前端—后端 API 兼容清单

## 读取规则与统一约定

清单来源固定为：

- 后端：`OnlineJudge/oj/urls.py`、各 app 的 `urls/*.py`、`OnlineJudge/utils/urls.py`、对应 View/Serializer/Form
- 前端：`OnlineJudgeFE/src/pages/oj/api.js`、`OnlineJudgeFE/src/pages/admin/api.js`、计划指定的上传/导入/编辑器组件

除特别注明外：

- 浏览器 Axios `baseURL` 是 `/api`，所以前端相对路径必须继续落到 `/api/...`；不得引入跨域 URL。
- 普通 `APIView` 的 POST/PUT 使用 JSON 或 URL encoded parser；GET/DELETE 使用 query string。
- 普通成功响应是 `{"error": null, "data": ...}`；错误是 `{"error": "<error-code>", "data": "<message>"}`。
- 分页参数保持 `limit`/`offset`，分页数据保持 `{"results": [...], "total": n}`。
- Axios 保持 `csrftoken` Cookie 与 `X-CSRFToken` Header。`CSRFExemptAPIView` 项目在表中明确标出。
- 测试文件列出主要覆盖位置；“未发现专门测试”不是删除或放宽协议的依据。
- 正则路由通常允许尾 `/`；本表用规范化路径书写。

## 账户与会话

| 方法 | 完整路径 | 调用端/权限 | 请求、Content-Type、CSRF | 成功 `data` | View / Serializer / 测试 |
|---|---|---|---|---|---|
| POST | `/api/login` | 用户端、管理端；匿名 | JSON：`username,password`，可选 `tfa_code`；普通 CSRF | `"Succeeded"`；需要二次认证时错误 data 为 `tfa_required` | `UserLoginAPI` / `UserLoginSerializer` / `account/tests.py` |
| GET | `/api/logout` | 用户端、管理端；无需登录 | 无请求体；不涉及 CSRF | `null` | `UserLogoutAPI` / `account/tests.py` |
| POST | `/api/register` | 用户端；匿名且站点允许注册 | JSON：`username,password,email,captcha`；普通 CSRF | `"Succeeded"` | `UserRegisterAPI` / `UserRegisterSerializer` / `account/tests.py` |
| GET | `/api/captcha` | 用户端；匿名 | 无 | 验证码 View 的当前 data 形状 | `CaptchaAPIView` / `account/tests.py::CaptchaTest` |
| POST | `/api/check_username_or_email` | 用户端；匿名 | JSON：`username`、`email` 至少一个；普通 CSRF | `{"username": bool, "email": bool}` | `UsernameOrEmailCheck` / `UsernameOrEmailCheckSerializer` / `account/tests.py` |
| GET | `/api/profile` | 用户端、管理端；匿名可取公开信息 | Query 可选 `username`；View 确保 CSRF Cookie | 未登录 `null`；登录/查用户为 `UserProfileSerializer` | `UserProfileAPI` / `account/tests.py` |
| PUT | `/api/profile` | 用户端；登录 | JSON：`real_name,avatar,blog,mood,github,school,major,language` 可选；普通 CSRF | 更新后的 profile serializer | `UserProfileAPI` / `EditUserProfileSerializer` / `account/tests.py` |
| GET | `/api/profile/fresh_display_id` | 用户端；登录 | 可传 `user_id`（当前 View 不使用）；普通 GET | `null` | `ProfileProblemDisplayIDRefreshAPI` / `account/tests.py` |
| POST | `/api/upload_avatar` | 用户端；登录 | multipart：`image`；普通 CSRF；图片格式 gif/jpg/jpeg/bmp/png，最大 2 MB | `"Succeeded"` | `AvatarUploadAPI` / `ImageUploadForm` / 无专门上传测试 |
| GET | `/api/tfa_required` | 用户端；匿名 | 无 | — | 不存在 GET，保持仅 POST |
| POST | `/api/tfa_required` | 用户端；匿名 | JSON：`username`；普通 CSRF | `{"result": bool}` | `CheckTFARequiredAPI` / `UsernameOrEmailCheckSerializer` / `account/tests.py` |
| GET | `/api/two_factor_auth` | 用户端；登录 | 无 | 二次认证二维码 base64 字符串 | `TwoFactorAuthAPI` / `account/tests.py` |
| POST | `/api/two_factor_auth` | 用户端；登录 | JSON：`code`；普通 CSRF | `"Succeeded"` | `TwoFactorAuthAPI` / `TwoFactorAuthCodeSerializer` / `account/tests.py` |
| PUT | `/api/two_factor_auth` | 用户端；登录 | JSON：`code`；普通 CSRF | `"Succeeded"` | `TwoFactorAuthAPI` / `TwoFactorAuthCodeSerializer` / `account/tests.py` |
| GET | `/api/sessions` | 用户端、管理端；登录 | 无 | 会话数组，含 `current_session,ip,user_agent,last_activity,session_key` | `SessionManagementAPI` / `account/tests.py` |
| DELETE | `/api/sessions` | 用户端；登录 | Query：`session_key` | `"Succeeded"` | `SessionManagementAPI` / `account/tests.py` |
| POST | `/api/change_password` | 用户端；登录 | JSON：`old_password,new_password`，2FA 时可选/必需 `tfa_code`；普通 CSRF | `"Succeeded"` | `UserChangePasswordAPI` / `UserChangePasswordSerializer` / `account/tests.py` |
| POST | `/api/change_email` | 用户端；登录 | JSON：`password,new_email`，2FA 时 `tfa_code`；普通 CSRF | `"Succeeded"` | `UserChangeEmailAPI` / `UserChangeEmailSerializer` / `account/tests.py` |
| POST | `/api/apply_reset_password` | 用户端；匿名 | JSON：`email,captcha`；普通 CSRF | `"Succeeded"` | `ApplyResetPasswordAPI` / `ApplyResetPasswordSerializer` / `account/tests.py` |
| POST | `/api/reset_password` | 用户端；匿名 | JSON：`token,password,captcha`；普通 CSRF | `"Succeeded"` | `ResetPasswordAPI` / `ResetPasswordSerializer` / `account/tests.py` |
| GET | `/api/user_rank` | 用户端；匿名 | Query：`offset,limit,rule`（ACM/OI） | `results/total`，结果为 RankInfo | `UserRankAPI` / `account/tests.py` |
| POST | `/api/open_api_appkey` | 用户端；登录且 OpenAPI 开启 | 无 JSON 字段；普通 CSRF | `{"appkey": "<runtime-value>"}`；值不进入文档/日志 | `OpenAPIAppkeyAPI` / `account/tests.py` |
| GET | `/api/sso`（兼容 `/api/ss`） | 用户端；登录 | 无 | 一次性 token 对象；不得记录真实值 | `SSOAPI` / 无专门测试 |
| POST | `/api/sso` | 外部 SSO 客户端；按 token 查用户 | JSON：`token`；CSRF exempt | `username,avatar,admin_type` | `SSOAPI` / `SSOSerializer` / 无专门测试 |

## 管理端账户、公告与配置

| 方法 | 完整路径 | 调用端/权限 | 请求、Content-Type、CSRF | 成功 `data` | View / Serializer / 测试 |
|---|---|---|---|---|---|
| GET | `/api/admin/user` | 管理端；超级管理员 | Query 可选 `id,keyword,paging,offset,limit` | 单用户 serializer 或 `results/total` | `UserAdminAPI` / `UserAdminSerializer` / `account/tests.py` |
| POST | `/api/admin/user` | 管理端；超级管理员 | JSON：`users`，每项 `[username,password,email,real_name]`；普通 CSRF | `null` | `UserAdminAPI` / `ImportUserSeralizer` / `account/tests.py` |
| PUT | `/api/admin/user` | 管理端；超级管理员 | JSON：`id,username,email,admin_type,problem_permission,is_disabled,password,open_api,two_factor_auth,real_name` | 用户 admin serializer | `UserAdminAPI` / `EditUserSerializer` / `account/tests.py` |
| DELETE | `/api/admin/user` | 管理端；超级管理员 | Query：`id`，支持逗号分隔 | `null` | `UserAdminAPI` / `account/tests.py` |
| GET | `/api/admin/generate_user` | 管理端；超级管理员 | Query：`file_id`；二进制 XLSX 下载 | XLSX 二进制，`application/xlsx` | `GenerateUserAPI` / `account/tests.py` |
| POST | `/api/admin/generate_user` | 管理端；超级管理员 | JSON：`prefix,suffix,number_from,number_to,password_length` | `{"file_id": "<runtime-id>"}` | `GenerateUserAPI` / `GenerateUserSerializer` / `account/tests.py` |
| GET | `/api/announcement` | 用户端；匿名 | Query：`offset,limit` | `results/total` | `AnnouncementAPI` / `AnnouncementSerializer` / `announcement/tests.py` |
| GET | `/api/admin/announcement` | 管理端；超级管理员 | Query 可选 `id,visible,offset,limit,paging` | 单公告或 `results/total` | `AnnouncementAdminAPI` / `announcement/tests.py` |
| POST | `/api/admin/announcement` | 管理端；超级管理员 | JSON：`title,content,visible`；普通 CSRF | 公告 serializer | `AnnouncementAdminAPI` / `CreateAnnouncementSerializer` / `announcement/tests.py` |
| PUT | `/api/admin/announcement` | 管理端；超级管理员 | JSON：`id,title,content,visible`；普通 CSRF | 更新后的公告 serializer | `AnnouncementAdminAPI` / `EditAnnouncementSerializer` / `announcement/tests.py` |
| DELETE | `/api/admin/announcement` | 管理端；超级管理员 | Query：`id` | `null` | `AnnouncementAdminAPI` / `announcement/tests.py` |
| GET | `/api/website` | 用户端；匿名 | 可带 query（当前 View 不使用） | 网站配置对象：`website_base_url,website_name,website_name_shortcut,website_footer,allow_register,submission_list_show_all` | `WebsiteConfigAPI` / `conf/tests.py` |
| GET | `/api/languages` | 用户端、管理端；匿名 | 无 | `{"languages": [], "spj_languages": []}` | `LanguagesAPI` / `conf/tests.py` |
| POST | `/api/judge_server_heartbeat/` | JudgeServer；CSRF exempt，摘要头认证 | JSON：见 [JudgeServer 协议](judge-server-protocol.md)；Header `X-Judge-Server-Token` | `{"error":null,"data":null}` | `JudgeServerHeartbeatAPI` / `JudgeServerHeartbeatSerializer` / `conf/tests.py` |
| GET | `/api/admin/smtp` | 管理端；超级管理员 | 无 | 未配置 `null`；已配置时不返回密码 | `SMTPAPI` / `conf/tests.py` |
| POST | `/api/admin/smtp` | 管理端；超级管理员 | JSON：`server,port,email,password,tls` | `null` | `SMTPAPI` / `CreateSMTPConfigSerializer` / `conf/tests.py` |
| PUT | `/api/admin/smtp` | 管理端；超级管理员 | JSON：`server,port,email,tls`，`password` 可选 | `null` | `SMTPAPI` / `EditSMTPConfigSerializer` / `conf/tests.py` |
| POST | `/api/admin/smtp_test` | 管理端；超级管理员 | JSON：`email` | `null` | `SMTPTestAPI` / `TestSMTPConfigSerializer` / 无专门测试 |
| GET | `/api/admin/website` | 管理端；View GET 未显式权限装饰器 | 无 | 网站配置对象 | `WebsiteConfigAPI` / `conf/tests.py` |
| POST | `/api/admin/website` | 管理端；超级管理员 | JSON：网站配置六字段；普通 CSRF | `null` | `WebsiteConfigAPI` / `CreateEditWebsiteConfigSerializer` / `conf/tests.py` |
| GET | `/api/admin/judge_server` | 管理端；超级管理员 | 无 | `{"token":"<runtime-value>","servers":[]}`；Token 值不得记录 | `JudgeServerAPI` / `JudgeServerSerializer` / `conf/tests.py` |
| PUT | `/api/admin/judge_server` | 管理端；超级管理员 | JSON：`id,is_disabled` | `null` | `JudgeServerAPI` / `EditJudgeServerSerializer` / `conf/tests.py` |
| DELETE | `/api/admin/judge_server` | 管理端；超级管理员 | Query：`hostname` | `null` | `JudgeServerAPI` / `conf/tests.py` |
| GET | `/api/admin/prune_test_case` | 管理端；超级管理员 | 无 | 孤立目录数组：`id,create_time` | `TestCasePruneAPI` / `conf/tests.py` |
| DELETE | `/api/admin/prune_test_case` | 管理端；超级管理员 | Query 可选 `id` | `null` | `TestCasePruneAPI` / `conf/tests.py` |
| GET | `/api/admin/versions` | 管理端页面；View 未显式权限装饰器 | 无 | 版本/release notes 对象或 `null` | `ReleaseNotesAPI` / `conf/tests.py` |
| GET | `/api/admin/dashboard_info` | 管理端页面；View 未显式权限装饰器 | 无 | `user_count,recent_contest_count,today_submission_count,judge_server_count,env` | `DashboardInfoAPI` / `conf/tests.py` |

## 问题、测试数据、导入导出

| 方法 | 完整路径 | 调用端/权限 | 请求、Content-Type、CSRF | 成功 `data`/响应 | View / Serializer / 测试 |
|---|---|---|---|---|---|
| GET | `/api/problem/tags` | 用户端、管理端；匿名 | Query 可选 `keyword` | Tag serializer 数组 | `ProblemTagAPI` / `problem/tests.py` |
| GET | `/api/problem` | 用户端；匿名，登录时增加 `my_status` | 详情 Query `problem_id`；列表必须 `limit`，可选 `offset,tag,keyword,difficulty,paging` | 详情 Problem serializer；列表 `results/total` | `ProblemAPI` / `ProblemSerializer` / `problem/tests.py` |
| GET | `/api/pickone` | 用户端；匿名 | 无 | 问题 display `_id` | `PickOneAPI` / 无专门测试 |
| GET | `/api/contest/problem` | 用户端竞赛；contest permission | Query：`contest_id`，可选 `problem_id` | 问题数组或详情；按权限为完整/安全 serializer | `problem.views.oj.ContestProblemAPI` / `contest/tests.py` |
| GET | `/api/admin/problem` | 管理端；problem permission | Query 单题 `id`；列表 `keyword,rule_type,offset,limit,paging` | 单题 admin serializer 或 `results/total` | `problem.views.admin.ProblemAPI` / `ProblemAdminSerializer` / `problem/tests.py` |
| POST | `/api/admin/problem` | 管理端；problem permission | JSON：`_id,title,description,input_description,output_description,samples,test_case_id,test_case_score,time_limit,memory_limit,languages,template,rule_type,io_mode,spj,spj_language,spj_code,spj_compile_ok,visible,difficulty,tags,hint,source,share_submission` | 新问题 admin serializer | `ProblemAPI` / `CreateProblemSerializer` / `problem/tests.py` |
| PUT | `/api/admin/problem` | 管理端；problem owner/permission | 上述问题字段加 `id`；普通 CSRF | 当前实现 `null` | `ProblemAPI` / `EditProblemSerializer` / `problem/tests.py` |
| DELETE | `/api/admin/problem` | 管理端；problem owner/permission | Query：`id` | `null` | `ProblemAPI` / `problem/tests.py` |
| GET | `/api/admin/contest/problem` | 管理端；竞赛创建者 | 单题 `id`；列表 `contest_id,keyword,offset,limit` | admin serializer 或 `results/total` | `ContestProblemAPI` / `problem/tests.py` |
| POST | `/api/admin/contest/problem` | 管理端；竞赛创建者 | 普通问题 JSON 加 `contest_id` | 新竞赛题 admin serializer | `ContestProblemAPI` / `CreateContestProblemSerializer` / `problem/tests.py` |
| PUT | `/api/admin/contest/problem` | 管理端；竞赛创建者 | 普通问题 JSON 加 `id,contest_id` | `null` | `ContestProblemAPI` / `EditContestProblemSerializer` / `problem/tests.py` |
| DELETE | `/api/admin/contest/problem` | 管理端；竞赛创建者 | Query：`id`；有提交时拒绝 | `null` | `ContestProblemAPI` / `problem/tests.py` |
| POST | `/api/admin/test_case` | 管理端页面；当前 POST 未显式权限装饰器；CSRF exempt | multipart：`file` ZIP、`spj` 字符串 `"true"`/其他；普通用例为 `1.in/1.out` 配对，SPJ 只有输入 | `{"id","info":[...],"spj":bool}`，info 含 input/output name、size、md5 | `TestCaseAPI` / `TestCaseUploadForm` / `problem/tests.py` |
| GET | `/api/admin/test_case` | 管理端；problem/contest owner；CSRF exempt | Query：`problem_id` | ZIP 二进制，`application/octet-stream`，包含 info | `TestCaseAPI` / `problem/tests.py`（下载覆盖有限） |
| POST | `/api/admin/compile_spj` | 管理端页面；View 未显式权限装饰器 | JSON：`spj_code,spj_language`；前端额外传 `id`，当前后端忽略；普通 CSRF | 成功 `null`；错误 data 为编译信息 | `CompileSPJAPI` / `CompileSPJSerializer` / 无专门测试 |
| POST | `/api/admin/contest_problem/make_public` | 管理端；problem permission | JSON：`id,display_id` | `null` | `MakeContestProblemPublicAPIView` / `ContestProblemMakePublicSerializer` / `problem/tests.py` |
| POST | `/api/admin/contest/add_problem_from_public` | 管理端页面；校验竞赛存在/未结束 | JSON：`contest_id,problem_id,display_id` | `null` | `AddContestProblemAPI` / `AddContestProblemSerializer` / `problem/tests.py` |
| GET | `/api/admin/export_problem` | 管理端；问题/竞赛 owner | Query 重复 `problem_id=1&problem_id=2`；普通 GET | 单题返回根目录单题 ZIP；多题返回由单题 ZIP 组成的批量 ZIP | `ExportProblemAPI` / `ExportProblemRequestSerialzier` / `ProblemZipImportAPITest` |
| POST | `/api/admin/import_problem` | 管理端页面；CSRF exempt；需要题目管理权限 | multipart：`file`；支持根目录单题 ZIP、由多个单题 ZIP 组成的批量 ZIP，并兼容 QDUOJ `N/problem.json` | `{"import_count": n, "package_format": "single\|batch\|qduoj", "imported": [...]}`；显示 ID 由 OJ 自动分配 | `ImportProblemAPI` / `UploadProblemForm,ImportProblemSerializer` / `ProblemZipImportAPITest` |
| POST | `/api/admin/import_fps` | 管理端页面；CSRF exempt；View 本身未显式权限装饰器 | multipart：`file`；FPS 输入 | `{"import_count": n}` | `FPSProblemImport` / `UploadProblemForm,FPSProblemSerializer` / 无专门测试 |
| POST | `/api/admin/upload_image` | Simditor；CSRF exempt，View 未要求登录 | multipart：`image` | 非统一包装：`{"success":true,"msg":"Success","file_path":"/..."}` | `SimditorImageUploadAPIView` / `ImageUploadForm` / 无专门测试 |
| POST | `/api/admin/upload_file` | Simditor；CSRF exempt，View 未要求登录 | multipart：`file` | 非统一包装：`success,msg,file_path,file_name` | `SimditorFileUploadAPIView` / `FileUploadForm` / 无专门测试 |

## 竞赛

| 方法 | 完整路径 | 调用端/权限 | 请求、Content-Type、CSRF | 成功 `data`/响应 | View / Serializer / 测试 |
|---|---|---|---|---|---|
| GET | `/api/contests` | 用户端；匿名 | Query：`offset,limit,keyword,rule_type,status` | `results/total` | `ContestListAPI` / `ContestSerializer` / `contest/tests.py` |
| GET | `/api/contest` | 用户端；匿名 | Query：`id` | Contest serializer 加 `now` | `ContestAPI` / `contest/tests.py` |
| POST | `/api/contest/password` | 用户端；登录 | JSON：`contest_id,password`；普通 CSRF | `true`，并写 server-side session | `ContestPasswordVerifyAPI` / `ContestPasswordVerifySerializer` / `contest/tests.py` |
| GET | `/api/contest/access` | 用户端；登录 | Query：`contest_id` | `{"access": bool}` | `ContestAccessAPI` / `contest/tests.py` |
| GET | `/api/contest/announcement` | 用户端竞赛；announcement permission | Query：`contest_id`，可选 `max_id` | 公告 serializer 数组 | `ContestAnnouncementListAPI` / `contest/tests.py` |
| GET | `/api/contest_rank` | 用户端竞赛；rank permission | Query：`contest_id,offset,limit`，可选 `download_csv,force_refresh` | 正常为 `results/total`；下载为 XLSX `application/xlsx` | `ContestRankAPI` / `ACM/OIContestRankSerializer` / `contest/tests.py` |
| GET | `/api/admin/contest` | 管理端；View GET 按 `ensure_created_by` 处理单项，未统一显式权限装饰 | 单项 `id`；列表 `keyword,offset,limit,paging` | admin serializer 或 `results/total` | `contest.views.admin.ContestAPI` / `contest/tests.py` |
| POST | `/api/admin/contest` | 管理端；方法未显式权限装饰，创建者来自 request user | JSON：`title,description,start_time,end_time,rule_type,password,visible,real_time_rank,allowed_ip_ranges` | Contest admin serializer | `ContestAPI` / `CreateConetestSeriaizer` / `contest/tests.py` |
| PUT | `/api/admin/contest` | 管理端；竞赛创建者 | JSON：上述字段加 `id` | Contest admin serializer | `ContestAPI` / `EditConetestSeriaizer` / `contest/tests.py` |
| DELETE | `/api/admin/contest` | 不支持 | 路由存在但 View 没有 `delete()`；保持当前不支持方法行为 | 不得假设成功包装 | `ContestAPI` / `contest/tests.py` |
| GET | `/api/admin/contest/announcement` | 管理端；竞赛创建者 | 单项 `id`；列表 `contest_id,keyword` | 单项 serializer 或公告数组 | `ContestAnnouncementAPI` / `contest/tests.py` |
| POST | `/api/admin/contest/announcement` | 管理端；竞赛创建者 | JSON：`contest_id,title,content,visible` | 公告 serializer | `ContestAnnouncementAPI` / `CreateContestAnnouncementSerializer` / `contest/tests.py` |
| PUT | `/api/admin/contest/announcement` | 管理端；公告所属竞赛创建者 | JSON：`id`，可选 `title,content,visible` | `null` | `ContestAnnouncementAPI` / `EditContestAnnouncementSerializer` / `contest/tests.py` |
| DELETE | `/api/admin/contest/announcement` | 管理端；管理员/竞赛创建者 | Query：`id` | `null` | `ContestAnnouncementAPI` / `contest/tests.py` |
| GET | `/api/admin/contest/acm_helper` | 用户端竞赛页面；rank permission | Query：`contest_id` | `id,username,real_name,problem_id,ac_info,checked` 数组 | `ACMContestHelper` / `contest/tests.py` |
| PUT | `/api/admin/contest/acm_helper` | 用户端竞赛页面；rank permission | JSON：`contest_id,problem_id,rank_id,checked` | `null` | `ACMContestHelper` / `ACMContesHelperSerializer` / 无专门测试 |
| GET | `/api/admin/download_submissions` | 管理端；竞赛创建者 | Query：`contest_id`，可选 `exclude_admin=1` | ZIP 二进制，`application/zip` | `DownloadContestSubmissions` / 无专门测试 |

## 提交

| 方法 | 完整路径 | 调用端/权限 | 请求、Content-Type、CSRF | 成功 `data` | View / Serializer / 测试 |
|---|---|---|---|---|---|
| POST | `/api/submission` | 用户端；登录，竞赛时还受竞赛权限/IP | JSON：`problem_id,language,code`，可选 `contest_id,captcha`；普通 CSRF | 普通 `{"submission_id": ...}`；竞赛隐藏题目 ID 时为 `null` | `SubmissionAPI` / `CreateSubmissionSerializer` / `submission/tests.py` |
| GET | `/api/submission` | 用户端；登录且有提交权限 | Query：`id` | 普通 ACM 可能为安全 serializer；OI/管理员为完整 serializer，加 `can_unshare` | `SubmissionAPI` / `submission/tests.py` |
| PUT | `/api/submission` | 用户端；提交拥有者/有权限 | JSON：`id,shared`；普通 CSRF | `null` | `SubmissionAPI` / `ShareSubmissionSerializer` / `submission/tests.py` |
| GET | `/api/submissions` | 用户端；匿名行为受配置和 request.user 影响 | 必须 Query `limit`；可选 `offset,problem_id,myself,username,result` | `results/total`，SubmissionListSerializer | `SubmissionListAPI` / `submission/tests.py` |
| GET | `/api/contest_submissions` | 用户端竞赛；submission permission | 必须 `contest_id,limit`；可选 `offset,problem_id,myself,username,result` | `results/total` | `ContestSubmissionListAPI` / `submission/tests.py` |
| GET | `/api/submission_exists` | 用户端；匿名可用 | Query：`problem_id` | 布尔值 | `SubmissionExistsAPI` / 无专门测试 |
| GET | `/api/admin/submission/rejudge` | 管理端；超级管理员 | Query：`id` | `null` | `SubmissionRejudgeAPI` / 无专门测试 |

## 数据库与路径不变量

阶段 0 只登记而不迁移：

- `INSTALLED_APPS` 的本地 app label 保持 `account, announcement, conf, problem, contest, utils, submission, options, judge`。
- 明确 `db_table` 必须保持：`user`、`user_profile`、`announcement`、`judge_server`、`problem_tag`、`problem`、`contest`、`acm_contest_rank`、`oi_contest_rank`、`contest_announcement`、`submission`。
- 历史迁移中曾创建、随后由迁移删除/替换的表名也属于不可重写的迁移契约：`contest_problem`、`judge_server_token`、`smtp_config`、`website_config`。阶段 1 只能纳管原文件，不能删除或重编号这些迁移。
- 未显式指定的 `SysOptions` 继续使用 Django 默认表名 `options_sysoptions`；内置 Django 表和中间表也不得因目录迁移重建。
- 迁移文件和迁移标识不得改名、删除或重新生成；当前只做 `showmigrations`/`migrate --plan` 检查。
- `/public` 继续指向运行时 `data/public`；测试数据继续由 `Problem.test_case_id` 解析到 `/data/test_case/<id>`，前端不得获得测试数据挂载。

## 计划端点别名与实际路由解析

阶段 00 计划文本列出的 `/api/upload_image/`、`/api/upload_file/` 是关注点名称；按当前 `OnlineJudge/oj/urls.py` 的 include 前缀和 `OnlineJudge/utils/urls.py`，实际可达完整路径是 `/api/admin/upload_image/`、`/api/admin/upload_file/`，本清单不凭计划别名发明未实现的 `/api/upload_*` 路由。后续如果要兼容无 `/admin` 的旧入口，必须另加显式代理/契约测试，而不是在目录迁移中悄悄改 View 路径。

## 已发现的历史兼容风险（仅登记，不在阶段 0 修复）

1. `OnlineJudgeFE/src/pages/admin/api.js` 的 `exportProblems` 封装调用 `POST /api/admin/export_problem`，但后端 `ExportProblemAPI` 只实现 GET；实际页面绕过该封装，使用 `/admin/export_problem?...` 下载。是否由旧 Web Server 重写该路径，需要后续部署验收确认。
2. Simditor 图片/文件上传使用 `success/msg/file_path` 包装，不是统一 `error/data` 包装；兼容层不得统一改写。
3. `test_case` 上传的 `spj` 是字符串 `"true"`/其他值，不要在目录切换中变成 JSON boolean 假设。
4. 若干 Admin View 的 GET/POST 没有显式装饰器；阶段 0 记录代码事实，不把未确认的网关/中间件权限推断成契约。
5. 心跳、Session/CSRF、JudgeServer `/judge`/`/compile_spj`/`/ping` 的完整字段见 [JudgeServer 协议](judge-server-protocol.md)。
