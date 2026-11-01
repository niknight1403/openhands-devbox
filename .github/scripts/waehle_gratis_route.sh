#!/usr/bin/env bash
# ============================================================================
# Gratis-Routen-Kaskade fuer OpenHands (headless).
#
# Zweck: OpenHands nicht an EINEN Anbieter binden. Das Skript probiert die
# kostenlosen OpenAI-kompatiblen Endpunkte in fester Prioritaetsreihenfolge,
# pingt jeden mit einem 1-Token-Prompt und uebernimmt den ersten, der
# wirklich antwortet. Ergebnis wird als LLM_URL / LLM_MODEL / LLM_KEY nach
# $GITHUB_ENV geschrieben.
#
# Schutzregeln:
#   - ausschliesslich kostenlose Routen (kein OpenAI-Paid noetig)
#   - Keys werden nie ausgegeben, nur "gesetzt"/"fehlt" geloggt
#   - kein Fremd-Endpunkt aus Nutzereingaben, nur die Liste unten
#
# Overrides (optional):
#   PREFERRED=gemini|groq|cerebras|mistral|openrouter|huggingface|pollinations
#   INPUT_MODEL=<litellm-modell-id>   (ueberschreibt das Modell der Route)
#   PING_TIMEOUT=<sekunden, default 20>
# ============================================================================
set -uo pipefail

PING_TIMEOUT="${PING_TIMEOUT:-20}"
PREFERRED="${PREFERRED:-}"
INPUT_MODEL="${INPUT_MODEL:-}"

# name|base_url|modell|litellm-prefix|key
# Reihenfolge = Prioritaet. Erst Schluessel der Nutzerin, am Ende keyfrei.
CANDIDATES=(
  "openrouter|https://openrouter.ai/api/v1|qwen/qwen3.8-27b:free|openrouter|${OPENROUTER_API_KEY:-}"
  "gemini|https://generativelanguage.googleapis.com/v1beta/openai|gemini-2.5-flash|openai|${GEMINI_API_KEY:-}"
  "groq|https://api.groq.com/openai/v1|llama-3.3-70b-versatile|openai|${GROQ_API_KEY:-}"
  "cerebras|https://api.cerebras.ai/v1|gpt-oss-120b|openai|${CEREBRAS_API_KEY:-}"
  "mistral|https://api.mistral.ai/v1|mistral-small-latest|openai|${MISTRAL_API_KEY:-}"
  "huggingface|https://router.huggingface.co/v1|openai/gpt-oss-120b:cerebras|openai|${HF_TOKEN:-}"
  "pollinations|https://text.pollinations.ai/openai|openai|openai|"
)

ping_route() {
  local url="$1" model="$2" key="$3"
  local -a auth=()
  [ -n "$key" ] && auth=(-H "Authorization: Bearer ${key}")
  local code
  code=$(curl -s -o /dev/null -m "$PING_TIMEOUT" -w '%{http_code}' \
    -X POST "${url%/}/chat/completions" \
    -H 'Content-Type: application/json' \
    "${auth[@]}" \
    -d "$(printf '{"model":"%s","messages":[{"role":"user","content":"ping"}],"max_tokens":1}' "$model")" \
    2>/dev/null)
  echo "${code:-000}"
}

echo "Gratis-Routen-Kaskade (Ping-Timeout ${PING_TIMEOUT}s)"
[ -n "$PREFERRED" ] && echo "Erzwungene Route: ${PREFERRED}"

TRIED=()
CHOSEN=""
for entry in "${CANDIDATES[@]}"; do
  IFS='|' read -r name url model prefix key <<< "$entry"
  [ -n "$PREFERRED" ] && [ "$name" != "$PREFERRED" ] && continue
  if [ "$name" != "pollinations" ] && [ -z "$key" ]; then
    TRIED+=("${name}: kein Key hinterlegt")
    continue
  fi
  code=$(ping_route "$url" "$model" "$key")
  if [ "$code" = "200" ]; then
    CHOSEN="${name}|${url}|${prefix}/${model}|${key}"
    echo "OK    ${name} antwortet (HTTP 200)"
    break
  fi
  TRIED+=("${name}: HTTP ${code}")
  echo "--    ${name} nicht nutzbar (HTTP ${code})"
done

if [ -z "$CHOSEN" ]; then
  echo "::error::Keine kostenlose Route erreichbar. Probiert:"
  for t in "${TRIED[@]}"; do echo "::error::  ${t}"; done
  echo "::error::Mindestens ein Secret hinterlegen (GEMINI_API_KEY, GROQ_API_KEY, CEREBRAS_API_KEY, MISTRAL_API_KEY, HF_TOKEN oder OPENROUTER_API_KEY)."
  exit 1
fi

IFS='|' read -r rname rurl rmodel rkey <<< "$CHOSEN"
[ -n "$INPUT_MODEL" ] && rmodel="$INPUT_MODEL"

echo "Gewaehlte Route: ${rname} | Modell: ${rmodel}"
if [ -n "${GITHUB_ENV:-}" ]; then
  {
    echo "LLM_URL=${rurl}"
    echo "LLM_MODEL=${rmodel}"
    echo "LLM_ROUTE_NAME=${rname}"
  } >> "$GITHUB_ENV"
  # Key nur ueber die Umgebung weiterreichen, nie ins Log.
  [ -n "$rkey" ] && echo "LLM_KEY=${rkey}" >> "$GITHUB_ENV"
fi
exit 0
