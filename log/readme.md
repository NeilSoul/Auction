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
segments buffer_size(seconds)
rate1, rate2, ..., ratek(Mbps)
price1, price2, ..., pricek
```

example
```
#B B A
41.7679789066
3 0.0
0.507960319519 0.507960319519 0.507960319519
23.6364384564 46.6957243367 69.1778576411
```

### transport
format
```
#T from_peer to_peer
timestamp(finished time!)
segment_index(from 0 to ..) segment_size(Mb) transport_duration(sconds)
```
example
```
#T A B
69.7660508156
3 0.732047080994 2.04561901093
```

## play.log

todo...