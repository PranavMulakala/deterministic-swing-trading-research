# Alpaca support question — draft only, not sent

Subject: Trading API fractional DAY protective orders for a $500 paper account

I'm evaluating an intraday-only, long-only strategy using the US Trading API,
not Broker API. My paper account reports ACTIVE, $500 equity and buying power,
multiplier=1, fractional_trading=true, and LITE fractionable=true. No leverage is
intended. Please confirm the currently supported behavior for this account type:

1. Can a fractional **qty** LITE buy limit DAY order include a broker-native OTO
   sell stop, or a bracket with a sell stop and take-profit limit? If not, are
   standalone fractional-qty sell stop DAY orders and fractional OCO exits supported?
2. Does the answer differ for qty versus notional? What minimum notional, quantity
   precision, price increments and stop-to-base-price constraints apply?
3. When an entry partially fills, when is protection activated, and for what
   filled quantity? Can a canceled or DAY-expired entry leave a partial position
   without an active protective stop?
4. Are these capabilities identical in paper and live environments? Is there a
   non-executing order-validation endpoint for the US Trading API?
5. For a $500, 1x/non-leveraged account, what current buying-power or settlement
   restrictions apply to fully funded intraday round trips? Are there account-
   specific restrictions beyond the published June 2026 PDT replacement?

Your fractional-trading guide and order/TIF table list fractional DAY limit and
stop orders, but the create-order reference still says fractional qty is only
supported for market/DAY. Please clarify which guidance is current, particularly
for linked protective orders.

I am not requesting an account reset, leverage change or an order submission.
I can supply account identification through your authenticated support channel;
no API key or secret is included here.

References:
- https://docs.alpaca.markets/us/docs/fractional-trading
- https://docs.alpaca.markets/us/docs/orders-at-alpaca
- https://docs.alpaca.markets/us/reference/postorder
