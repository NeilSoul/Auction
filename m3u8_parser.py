import m3u8


class LengthMismatch(Exception):
    pass


def parse_m3u8_novar(url, string=None):
    """Parse the m3u8 without variable bitrates and return a list of URLs."""
    if not string:
        m3u8_obj = m3u8.load(url)
    else:
        m3u8_obj = m3u8.loads(string)
        m3u8_obj.base_uri = url.rsplit('/', maxsplit=1)[0] + '/'
    return [m3u8_obj.base_uri + uri for uri in m3u8_obj.segments.uri]


def parse_m3u8(url):
    """Parse the m3u8 and return the URLs of the video segments.

    The return value is a list, of which each item is a dict: bandwidth -> url.
    The bandwidth defaults to 0 if there is no choice of bitrates.

    e.g.
    [
        {0: "http://example.com/01.ts"},
        {0: "http://example.com/02.ts"}
    ] (no choice),
    or
    [
        {
            734721: "http://example.com/360p/01.ts",
            1476340: "http://example.com/720p/01.ts"
        },
        {
            734721: "http://example.com/360p/02.ts",
            1476340: "http://example.com/720p/02.ts"
        }
    ] (with choice),
    """
    m3u8_obj = m3u8.load(url)

    # no choice
    if not m3u8_obj.is_variant:
        return [{0: uri} for uri in parse_m3u8_novar(url, m3u8_obj.dumps())]

    # with choice
    filelist = []
    try:
        for pl in m3u8_obj.playlists:
            newlist = parse_m3u8_novar(url=pl.absolute_uri)
            bw = pl.stream_info.bandwidth
            if not filelist:
                filelist = [{bw: uri} for uri in newlist]
            else:
                if len(newlist) != len(filelist):
                    raise LengthMismatch
                for i in range(len(filelist)):
                    filelist[i][bw] = newlist[i]
        return filelist
    except LengthMismatch:
        print("Failed to parse m3u8. Length mismatch.")


# unit test
if __name__ == "__main__":
    url_var = "http://devimages.apple.com/iphone/samples/bipbop/bipbopall.m3u8"
    print(parse_m3u8(url=url_var))
