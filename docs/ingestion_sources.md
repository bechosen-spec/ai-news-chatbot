# Nigerian news ingestion sources

## Integrated: Punch Newspapers

Punch provides an [official RSS directory](https://rss.punchng.com/) describing feeds as a mechanism
for applications to access site updates. The directory also states that Punch may discontinue feeds
and governs their use. The integration was verified on 2 November 2026 against the live RSS 2.0
endpoints.

The enabled endpoint is `https://rss.punchng.com/v1/category/latest_news`. The directory also lists
politics, business, sports, technology, and entertainment endpoints. During live verification the
business endpoint returned a valid but empty channel and politics intermittently timed out, so those
category endpoints are documented but deliberately not enabled. Application categories come from
the separately stored SVM prediction, not an invented source category.

The adapter stores title, bounded RSS excerpt, author, source category, canonical original URL,
publication and collection times, optional enclosure URL, feed URL, and RSS GUID. It stores an empty
article-body field and directs readers to the publisher for the full story. Tracking parameters are
removed without altering the canonical publisher path.

The feed is retried at most three times by default with bounded exponential backoff and a 15-second
request timeout. An outage becomes an `ingestion_failure` rather than crashing the platform. The
generic adapter can isolate and interleave multiple feeds when additional endpoints are verified.
Incremental runs check both canonical URL and source/external ID, backed by database constraints.

## Investigated but not integrated

Premium Times, Channels Television, The Guardian Nigeria, Vanguard, and Daily Trust remain candidates.
They were not added because this milestone did not verify an equally explicit, stable publisher feed
directory and usage basis for each. The system does not scrape their websites or infer permission
from the existence of a WordPress-style URL. Adding a source requires documented feed/API ownership,
terms review, domain allow-listing, fixture coverage, and a live bounded smoke test.

## Copyright and attribution

RSS availability is not permission to republish full articles. The application stores only feed
metadata and bounded excerpts, names Punch on every response, preserves the original URL, and includes
a full-article-at-source notice. No paywall, robots control, or anti-bot mechanism is bypassed.

