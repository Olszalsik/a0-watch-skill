### ws_search
hybrid keyword+semantic search across every indexed video (video intelligence)
args: `query` (required), optional `limit` (default 10)
use when the user asks "find the moment in any video where X" and you don't know which video holds the answer
follow each hit with `ws_ask` (or `ws_moment`) on the returned video_id + timestamp
example:
~~~json
{
  "thoughts": ["Search the whole library for the phrase."],
  "headline": "Searching video library",
  "tool_name": "ws_search",
  "tool_args": {
    "query": "deployment pipeline failure"
  }
}
~~~