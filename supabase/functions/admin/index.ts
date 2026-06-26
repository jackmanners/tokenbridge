import { createClient } from '@supabase/supabase-js'

const cors = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

function jsonResp(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...cors, 'Content-Type': 'application/json' },
  })
}

function authorized(req: Request): boolean {
  const apiKey = Deno.env.get('TOKENBRIDGE_API_KEY')
  return !!apiKey && req.headers.get('Authorization') === `Bearer ${apiKey}`
}

Deno.serve(async (req) => {
  if (req.method === 'OPTIONS') return new Response('ok', { headers: cors })

  const url = new URL(req.url)
  const action = url.searchParams.get('action')

  if (req.method === 'GET' && !action) {
    const fnBase = (Deno.env.get('SUPABASE_URL') ?? '') + '/functions/v1'
    return new Response(buildHtml(fnBase), {
      headers: { 'Content-Type': 'text/html; charset=utf-8' },
    })
  }

  if (!authorized(req)) return jsonResp({ error: 'unauthorized' }, 401)

  const supabase = createClient(
    Deno.env.get('SUPABASE_URL')!,
    Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!,
  )

  if (action === 'participants') {
    const q = (url.searchParams.get('q') ?? '').trim()
    let query = supabase
      .from('oauth_tokens')
      .select('user_id, provider, updated_at, expires_at')
      .order('user_id')
    if (q && q !== '__ping__') query = query.ilike('user_id', `%${q}%`)
    const { data, error } = await query
    if (error) return jsonResp({ error: error.message }, 500)

    const map: Record<string, { user_id: string; providers: unknown[] }> = {}
    for (const row of data ?? []) {
      if (!map[row.user_id]) map[row.user_id] = { user_id: row.user_id, providers: [] }
      map[row.user_id].providers.push({
        provider: row.provider,
        updated_at: row.updated_at,
        expires_at: row.expires_at,
        expired: row.expires_at ? new Date(row.expires_at) < new Date() : false,
      })
    }
    return jsonResp(Object.values(map))
  }

  return jsonResp({ error: 'unknown action' }, 400)
})

function buildHtml(fnBase: string): string {
  return '<!DOCTYPE html>\n' +
'<html lang="en">\n' +
'<head>\n' +
'<meta charset="UTF-8">\n' +
'<meta name="viewport" content="width=device-width,initial-scale=1">\n' +
'<title>TokenBridge Admin</title>\n' +
'<style>\n' +
'*{box-sizing:border-box;margin:0;padding:0}\n' +
'body{font-family:system-ui,sans-serif;font-size:13px;background:#f1f5f9;color:#0f172a;min-height:100vh}\n' +
'header{background:#0f172a;color:#f1f5f9;padding:14px 24px;display:flex;align-items:center;gap:12px}\n' +
'header h1{font-size:15px;font-weight:700}\n' +
'.wrap{max-width:760px;margin:24px auto;padding:0 16px}\n' +
'.card{background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:16px;margin-bottom:14px}\n' +
'label{display:block;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.05em;color:#64748b;margin-bottom:4px}\n' +
'input,select{width:100%;padding:7px 10px;border:1px solid #e2e8f0;border-radius:6px;font-size:13px;font-family:inherit;outline:none}\n' +
'input:focus,select:focus{border-color:#3b82f6;box-shadow:0 0 0 2px #eff6ff}\n' +
'.row{display:flex;gap:8px;align-items:flex-end}\n' +
'.row>*{flex:1}\n' +
'button{padding:7px 14px;border-radius:6px;border:1px solid #e2e8f0;background:#fff;font-size:12px;font-weight:500;cursor:pointer;font-family:inherit;white-space:nowrap;flex:0}\n' +
'button.primary{background:#0f172a;color:#fff;border-color:#0f172a}\n' +
'button:hover{opacity:.85}\n' +
'.participant{border:1px solid #e2e8f0;border-radius:8px;margin-bottom:8px;overflow:hidden}\n' +
'.p-head{padding:10px 14px;background:#f8fafc;display:flex;align-items:center;gap:8px;cursor:pointer}\n' +
'.p-id{font-weight:700;font-size:13px;flex:1}\n' +
'.p-body{padding:10px 14px;display:none}\n' +
'.p-body.open{display:block}\n' +
'.provider-row{display:flex;align-items:center;gap:10px;padding:6px 0;border-bottom:1px solid #f1f5f9;flex-wrap:wrap}\n' +
'.provider-row:last-child{border-bottom:none}\n' +
'.pname{font-weight:600;width:130px;flex-shrink:0}\n' +
'.pstatus{font-size:11px;color:#64748b;flex:1}\n' +
'.tag{font-size:10px;padding:2px 7px;border-radius:10px;font-weight:600;display:inline-block;margin-right:4px}\n' +
'.tag.ok{background:#dcfce7;color:#166534}\n' +
'.tag.exp{background:#fee2e2;color:#991b1b}\n' +
'.url-box{margin-top:6px;width:100%;padding:7px 9px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px;font-size:11px;word-break:break-all;color:#334155;font-family:monospace}\n' +
'.hint{font-size:11px;color:#64748b;margin-top:6px}\n' +
'#lock{position:fixed;inset:0;background:#f1f5f9;display:flex;align-items:center;justify-content:center;z-index:99}\n' +
'#lock .card{max-width:340px;width:100%}\n' +
'#lock h2{font-size:15px;font-weight:700;margin-bottom:12px}\n' +
'#status{font-size:11px;color:#dc2626;margin-top:6px;min-height:16px}\n' +
'</style>\n' +
'</head>\n' +
'<body>\n' +
'\n' +
'<div id="lock">\n' +
'  <div class="card">\n' +
'    <h2>TokenBridge Admin</h2>\n' +
'    <label>API Key</label>\n' +
'    <input type="password" id="key-input" placeholder="tbk-..." autocomplete="current-password">\n' +
'    <div id="status"></div>\n' +
'    <button class="primary" style="margin-top:10px;width:100%" id="unlock-btn">Unlock</button>\n' +
'  </div>\n' +
'</div>\n' +
'\n' +
'<header>\n' +
'  <div>&#x1F309;</div>\n' +
'  <h1>TokenBridge Admin</h1>\n' +
'</header>\n' +
'\n' +
'<div class="wrap">\n' +
'  <div class="card">\n' +
'    <label>Search participants</label>\n' +
'    <div class="row">\n' +
'      <input id="search" placeholder="user ID (partial match)">\n' +
'      <button id="search-btn">Search</button>\n' +
'    </div>\n' +
'  </div>\n' +
'  <div id="results"></div>\n' +
'  <div class="card">\n' +
'    <label>Generate auth link</label>\n' +
'    <div class="row" style="margin-bottom:8px">\n' +
'      <div><label>User ID</label><input id="new-uid" placeholder="e.g. p001"></div>\n' +
'      <div><label>Provider</label><select id="new-provider">\n' +
'        <option value="google-health">Google Health</option>\n' +
'        <option value="withings">Withings</option>\n' +
'        <option value="oura">Oura</option>\n' +
'      </select></div>\n' +
'      <button class="primary" id="gen-btn">Get link</button>\n' +
'    </div>\n' +
'    <div class="hint">User ID is normalized to lowercase. Opens a new link even if the participant already exists.</div>\n' +
'    <div id="new-url-box" class="url-box" style="display:none"></div>\n' +
'  </div>\n' +
'</div>\n' +
'\n' +
'<script>\n' +
'var FN_BASE = "' + fnBase + '";\n' +
'var API_KEY = sessionStorage.getItem("tb_key") || "";\n' +
'var searchTimer;\n' +
'\n' +
'function unlock() {\n' +
'  var k = document.getElementById("key-input").value.trim();\n' +
'  if (!k) return;\n' +
'  document.getElementById("status").textContent = "Checking...";\n' +
'  fetch(FN_BASE + "/admin?action=participants&q=__ping__", {\n' +
'    headers: { "Authorization": "Bearer " + k }\n' +
'  }).then(function(r) {\n' +
'    if (r.status === 401) { document.getElementById("status").textContent = "Wrong key."; return; }\n' +
'    API_KEY = k;\n' +
'    sessionStorage.setItem("tb_key", k);\n' +
'    document.getElementById("lock").style.display = "none";\n' +
'    doSearch();\n' +
'  }).catch(function() { document.getElementById("status").textContent = "Connection error."; });\n' +
'}\n' +
'\n' +
'document.getElementById("unlock-btn").onclick = unlock;\n' +
'document.getElementById("key-input").onkeydown = function(e) { if (e.key === "Enter") unlock(); };\n' +
'document.getElementById("search-btn").onclick = doSearch;\n' +
'document.getElementById("search").oninput = function() { clearTimeout(searchTimer); searchTimer = setTimeout(doSearch, 300); };\n' +
'document.getElementById("gen-btn").onclick = generateUrl;\n' +
'\n' +
'if (API_KEY) { document.getElementById("lock").style.display = "none"; doSearch(); }\n' +
'\n' +
'function doSearch() {\n' +
'  var q = document.getElementById("search").value.trim();\n' +
'  fetch(FN_BASE + "/admin?action=participants&q=" + encodeURIComponent(q), {\n' +
'    headers: { "Authorization": "Bearer " + API_KEY }\n' +
'  }).then(function(r) { return r.json(); }).then(renderResults);\n' +
'}\n' +
'\n' +
'function renderResults(data) {\n' +
'  var el = document.getElementById("results");\n' +
'  if (!data.length) { el.innerHTML = "<div class=\\"card\\" style=\\"color:#64748b\\">No participants found.</div>"; return; }\n' +
'  el.innerHTML = "";\n' +
'  data.forEach(function(p) {\n' +
'    var div = document.createElement("div");\n' +
'    div.className = "participant";\n' +
'    var head = document.createElement("div");\n' +
'    head.className = "p-head";\n' +
'    head.innerHTML = "<span class=\\"p-id\\">" + p.user_id + "</span><span style=\\"font-size:11px;color:#64748b\\">" + p.providers.map(function(pr){return pr.provider;}).join(", ") + "</span><button onclick=\\"prefill(\'" + p.user_id + "\')\\" style=\\"font-size:11px\\">+ add provider</button>";\n' +
'    var body = document.createElement("div");\n' +
'    body.className = "p-body";\n' +
'    p.providers.forEach(function(pr) {\n' +
'      var row = document.createElement("div");\n' +
'      row.className = "provider-row";\n' +
'      var tag = pr.expired ? "<span class=\\"tag exp\\">expired</span>" : "<span class=\\"tag ok\\">active</span>";\n' +
'      var updated = pr.updated_at ? new Date(pr.updated_at).toLocaleDateString() : "—";\n' +
'      row.innerHTML = "<span class=\\"pname\\">" + pr.provider + "</span><span class=\\"pstatus\\">" + tag + " updated " + updated + "</span>";\n' +
'      var btn = document.createElement("button");\n' +
'      btn.textContent = "New link";\n' +
'      btn.onclick = (function(uid, prov, r) { return function() { getUrlInto(uid, prov, r); }; })(p.user_id, pr.provider, row);\n' +
'      row.appendChild(btn);\n' +
'      body.appendChild(row);\n' +
'    });\n' +
'    head.onclick = function(e) { if (e.target.tagName === "BUTTON") return; body.classList.toggle("open"); };\n' +
'    div.appendChild(head);\n' +
'    div.appendChild(body);\n' +
'    el.appendChild(div);\n' +
'  });\n' +
'}\n' +
'\n' +
'function getUrlInto(uid, provider, container) {\n' +
'  var box = container.querySelector(".url-box") || document.createElement("div");\n' +
'  box.className = "url-box";\n' +
'  box.textContent = "Generating...";\n' +
'  if (!container.querySelector(".url-box")) container.appendChild(box);\n' +
'  fetchAuthUrl(uid, provider).then(function(url) {\n' +
'    box.innerHTML = "<a href=\\"" + url + "\\" target=\\"_blank\\">" + url + "</a>";\n' +
'  });\n' +
'}\n' +
'\n' +
'function prefill(uid) {\n' +
'  document.getElementById("new-uid").value = uid;\n' +
'  document.getElementById("auth-section") && document.getElementById("auth-section").scrollIntoView({behavior:"smooth"});\n' +
'}\n' +
'\n' +
'function generateUrl() {\n' +
'  var uid = document.getElementById("new-uid").value.trim().toLowerCase();\n' +
'  var provider = document.getElementById("new-provider").value;\n' +
'  if (!uid) { alert("Enter a user ID"); return; }\n' +
'  var box = document.getElementById("new-url-box");\n' +
'  box.style.display = "block";\n' +
'  box.textContent = "Generating...";\n' +
'  fetchAuthUrl(uid, provider).then(function(url) {\n' +
'    box.innerHTML = "<a href=\\"" + url + "\\" target=\\"_blank\\">" + url + "</a>";\n' +
'  });\n' +
'}\n' +
'\n' +
'function fetchAuthUrl(uid, provider) {\n' +
'  return fetch(FN_BASE + "/auth-start?user_id=" + encodeURIComponent(uid) + "&provider=" + provider + "&format=json", {\n' +
'    headers: { "Authorization": "Bearer " + API_KEY }\n' +
'  }).then(function(r) { return r.json(); }).then(function(d) { return d.url; });\n' +
'}\n' +
'</script>\n' +
'</body>\n' +
'</html>\n'
}
