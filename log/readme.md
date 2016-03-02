# Introduction of log

## auction.log

auction event entry.

### auction broadcast
format
```
#A auctioneer_peer
timestamp(second)
segments capacity(Mbps) cti cda cwda
```
example
```
#A A
4.96642613411
3 1 0.15 0.15 0.01
```

### auction decision
format
```
#D auctioneer_peer bidder_peer
timestamp
segments bitrate payment
```

example
```
#D A B
5.88063812256
3 0.296698570251 52.483137373
```

### bid
format
```
#B bidder_peer auction_peer
timestamp 
segments
rate1, rate2, ..., ratek(Mbps)
price1, price2, ..., pricek
```

example
```
#B B A
5.80487298965
3
0.296698570251 0.296698570251 0.296698570251
17.8943791243 35.3887582487 52.483137373
```

### transport
format
```
#T from_peer to_peer
timestamp(finished time!)
segment_size(Mb) transport_duration(sconds)
```
example
```
#T A B
11.1779739857
0.395339012146 0.844485044479
```

## play.log

todo...