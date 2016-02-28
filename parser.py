import m3u8


def parse_m3u8_novar(url, string=None):
    """Parse m3u8 without variable bitrates and return durations and URLs.

    The return value is a (float, str) tuple of duration and URL.
    """
    if not string:
        m3u8_obj = m3u8.load(url)
    else:
        m3u8_obj = m3u8.loads(string)
        m3u8_obj.base_uri = url.rsplit('/', maxsplit=1)[0] + '/'
    return [(seg.duration, m3u8_obj.base_uri + seg.uri)
            for seg in m3u8_obj.segments]


def parse_m3u8(url):
    """Parse the m3u8 and return the URLs of the video segments.

    The return value is a (float, dict) tuple,
    in which the float is the duration of the segment,
    dict: int -> str maps the bandwidth to the url.
    The bandwidth defaults to 0 if there is no choice of bitrates.

    e.g.
    [
        (5.0, {0: "http://example.com/01.ts"}),
        (5.0, {0: "http://example.com/02.ts"})
    ] (no choice),
    or
    [
        (5.0, {
            734721: "http://example.com/360p/01.ts",
            1476340: "http://example.com/720p/01.ts"
        }),
        (5.0, {
            734721: "http://example.com/360p/02.ts",
            1476340: "http://example.com/720p/02.ts"
        })
    ] (with choice),
    """
    m3u8_obj = m3u8.load(url)

    # no choice
    if not m3u8_obj.is_variant:
        return [(item[0], {0: item[1]}) for item in
                parse_m3u8_novar(url, m3u8_obj.dumps())]

    # with choice
    infolist = []
    try:
        for pl in m3u8_obj.playlists:
            newlist = parse_m3u8_novar(url=pl.absolute_uri)
            bw = pl.stream_info.bandwidth
            if not infolist:
                infolist = [(item[0], {bw: item[1]}) for item in newlist]
            else:
                if len(newlist) != len(infolist):
                    raise ValueError
                for i in range(len(infolist)):
                    if newlist[i][0] != infolist[i][0]:
                        raise ValueError
                    infolist[i][1][bw] = newlist[i][1]
        return infolist
    except ValueError:
        print("Failed to parse m3u8. Segment length or count mismatch.")


# unit test
if __name__ == "__main__":
    url_var = "http://devimages.apple.com/iphone/samples/bipbop/bipbopall.m3u8"
    print(parse_m3u8(url=url_var))
