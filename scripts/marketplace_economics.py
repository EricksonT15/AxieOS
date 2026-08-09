import argparse
from datetime import datetime
from database import connect_database


def get_marketplace_event_counts(conn):
    return conn.execute(
        """
        SELECT
            event_type,
            COUNT(*) AS event_count
        FROM marketplace_events
        GROUP BY event_type
        ORDER BY event_type
        """
    ).fetchall()


def get_axie_position_counts(conn):
    return conn.execute(
        """
        SELECT
            SUM(
                CASE
                    WHEN sale.id IS NOT NULL THEN 1
                    ELSE 0
                END
            ) AS completed_positions,

            SUM(
                CASE
                    WHEN sale.id IS NULL THEN 1
                    ELSE 0
                END
            ) AS open_positions

        FROM marketplace_events buy

        LEFT JOIN marketplace_events sale
          ON buy.asset_id = sale.asset_id
         AND sale.event_type = 'sale'

        WHERE buy.event_type = 'buy'
          AND buy.asset_type = 'Axie'
        """
    ).fetchone()


def get_open_axie_capital(conn):
    return conn.execute(
        """
        SELECT
            COUNT(*) AS open_count,
            SUM(CAST(buy.amount AS REAL)) AS deployed_eth
        FROM marketplace_events buy

        LEFT JOIN marketplace_events sale
          ON buy.asset_id = sale.asset_id
         AND sale.event_type = 'sale'

        WHERE buy.event_type = 'buy'
          AND buy.asset_type = 'Axie'
          AND sale.id IS NULL
        """
    ).fetchone()

def get_open_axie_target_value(conn):
    return conn.execute(
        """
        SELECT
            SUM(CAST(buy.amount AS REAL)) AS deployed_eth,
            SUM(
                CAST(
                    (
                        SELECT list.amount
                        FROM marketplace_events list
                        WHERE list.asset_id = buy.asset_id
                          AND list.event_type = 'list'
                        ORDER BY list.id DESC
                        LIMIT 1
                    ) AS REAL
                )
            ) AS target_eth
        FROM marketplace_events buy

        LEFT JOIN marketplace_events sale
          ON buy.asset_id = sale.asset_id
         AND sale.event_type = 'sale'

        WHERE buy.event_type = 'buy'
          AND buy.asset_type = 'Axie'
          AND sale.id IS NULL
        """
    ).fetchone()


def get_open_axie_positions(conn):
    return conn.execute(
        """
        SELECT
            buy.asset_id,
            buy.asset_name,
            CAST(buy.amount AS REAL) AS buy_price,

            CAST(
                (
                    SELECT list.amount
                    FROM marketplace_events list
                    WHERE list.asset_id = buy.asset_id
                      AND list.event_type = 'list'
                    ORDER BY list.id DESC
                    LIMIT 1
                ) AS REAL
            ) AS list_price

        FROM marketplace_events buy

        LEFT JOIN marketplace_events sale
          ON buy.asset_id = sale.asset_id
         AND sale.event_type = 'sale'

        WHERE buy.event_type = 'buy'
          AND buy.asset_type = 'Axie'
          AND sale.id IS NULL

        ORDER BY buy.id
        """
    ).fetchall()


def get_completed_axie_positions(conn):
    return conn.execute(
        """
        SELECT
            buy.asset_id,
            buy.asset_name,
            CAST(buy.amount AS REAL) AS buy_price,
            CAST(sale.amount AS REAL) AS sale_price,
            buy.event_datetime AS buy_time,
            sale.event_datetime AS sale_time

        FROM marketplace_events buy

        JOIN marketplace_events sale
          ON buy.asset_id = sale.asset_id
         AND sale.event_type = 'sale'

        WHERE buy.event_type = 'buy'
          AND buy.asset_type = 'Axie'

        ORDER BY sale.id
        """
    ).fetchall()


def get_completed_axie_totals(conn):
    return conn.execute(
        """
        SELECT
            COUNT(*) AS completed_count,
            SUM(CAST(buy.amount AS REAL)) AS total_buy_eth,
            SUM(CAST(sale.amount AS REAL)) AS total_sale_eth
        FROM marketplace_events buy

        JOIN marketplace_events sale
          ON buy.asset_id = sale.asset_id
         AND sale.event_type = 'sale'

        WHERE buy.event_type = 'buy'
          AND buy.asset_type = 'Axie'
        """
    ).fetchone()


def main():


    parser = argparse.ArgumentParser(
        description="AxieOS marketplace economic analytics."
    )

    parser.add_argument(
        "--fee-rate",
        type=float,
        default=0.0,
        help="Marketplace selling fee percentage, for example 4.25.",
    )

    args = parser.parse_args()

    fee_rate = args.fee_rate / 100

    conn = connect_database()

    event_counts = get_marketplace_event_counts(conn)
    axie_positions = get_axie_position_counts(conn)
    open_axie_capital = get_open_axie_capital(conn)
    open_axie_target = get_open_axie_target_value(conn)
    open_axies = get_open_axie_positions(conn)
    completed_axies = get_completed_axie_positions(conn)
    completed_totals = get_completed_axie_totals(conn)
    completed_count = completed_totals[0] or 0
    total_buy_eth = completed_totals[1] or 0
    total_sale_eth = completed_totals[2] or 0

    total_selling_fees = total_sale_eth * fee_rate
    total_net_proceeds = total_sale_eth - total_selling_fees
    total_net_profit = total_net_proceeds - total_buy_eth

    total_net_roi = (
        total_net_profit / total_buy_eth * 100
        if total_buy_eth > 0
        else 0
    )


    print("AXIEOS MARKETPLACE ECONOMICS")
    print("-" * 60)

    for event_type, count in event_counts:
        print(f"{event_type}: {count}")

    print()
    print("AXIE POSITIONS")
    print("-" * 60)
    print(f"Completed: {axie_positions[0] or 0}")
    print(f"Open: {axie_positions[1] or 0}")  
    print()
    print("OPEN AXIE CAPITAL")
    print("-" * 60)
    print(
        f"Open positions: "
        f"{open_axie_capital[0] or 0}"
    )
    print(
        f"Deployed ETH: "
        f"{open_axie_capital[1] or 0:.8f}"
    )


    deployed_eth = open_axie_target[0] or 0
    target_eth = open_axie_target[1] or 0

    gross_spread = target_eth - deployed_eth

    gross_roi = (
        gross_spread / deployed_eth * 100
        if deployed_eth > 0
        else 0
    )

    

    estimated_fee = target_eth * fee_rate
    net_target_eth = target_eth - estimated_fee
    net_profit = net_target_eth - deployed_eth

    net_roi = (
        net_profit / deployed_eth * 100
        if deployed_eth > 0
        else 0
    )





    print()
    print("OPEN AXIE TARGET VALUE")
    print("-" * 60)
    print(f"Deployed ETH: {deployed_eth:.8f}")
    print(f"Target ETH: {target_eth:.8f}")
    print(f"Target gross spread: {gross_spread:+.8f}")
    print(f"Target gross ROI: {gross_roi:.2f}%")
    print(f"Marketplace fee rate: {args.fee_rate:.2f}%")
    print(f"Estimated selling fee: {estimated_fee:.8f} ETH")
    print(f"Net target proceeds: {net_target_eth:.8f} ETH")
    print(f"Net target profit: {net_profit:+.8f} ETH")
    print(f"Net target ROI: {net_roi:.2f}%")
    print()


    print("OPEN AXIE POSITION DETAILS")
    print("-" * 60)

    for asset_id, asset_name, buy_price, list_price in open_axies:
        if list_price is None:
            print(f"{asset_name} #{asset_id}")
            print(f"  Buy price: {buy_price:.8f} ETH")
            print("  No active listing found")
            print()
            continue

        gross_profit = list_price - buy_price

        gross_roi = (
            gross_profit / buy_price * 100
            if buy_price > 0
            else 0
        )

        selling_fee = list_price * fee_rate
        net_proceeds = list_price - selling_fee
        net_profit = net_proceeds - buy_price

        net_roi = (
            net_profit / buy_price * 100
            if buy_price > 0
            else 0
        )

        print(f"{asset_name} #{asset_id}")
        print(f"  Buy price: {buy_price:.8f} ETH")
        print(f"  List price: {list_price:.8f} ETH")
        print(f"  Gross profit: {gross_profit:+.8f} ETH")
        print(f"  Gross ROI: {gross_roi:.2f}%")
        print(f"  Selling fee: {selling_fee:.8f} ETH")
        print(f"  Net profit: {net_profit:+.8f} ETH")
        print(f"  Net ROI: {net_roi:.2f}%")
        print()


    print()
    print("REALIZED AXIE TRADING SUMMARY")
    print("-" * 60)
    print(f"Completed trades: {completed_count}")
    print(f"Total capital deployed: {total_buy_eth:.8f} ETH")
    print(f"Total sale proceeds: {total_sale_eth:.8f} ETH")
    print(f"Estimated selling fees: {total_selling_fees:.8f} ETH")
    print(f"Net proceeds: {total_net_proceeds:.8f} ETH")
    print(f"Net profit: {total_net_profit:+.8f} ETH")
    print(f"Net ROI: {total_net_roi:.2f}%")




    print()
    print("COMPLETED AXIE TRADE DETAILS")
    print("-" * 60)

    for (
        asset_id,
        asset_name,
        buy_price,
        sale_price,
        buy_time,
        sale_time,
    ) in completed_axies:

        gross_profit = sale_price - buy_price

        gross_roi = (
            gross_profit / buy_price * 100
            if buy_price > 0
            else 0
        )

        selling_fee = sale_price * fee_rate
        net_proceeds = sale_price - selling_fee
        net_profit = net_proceeds - buy_price

        net_roi = (
            net_profit / buy_price * 100
            if buy_price > 0
            else 0
        )

        holding_time = "Unknown"

        if buy_time and sale_time:
            bought_at = datetime.fromisoformat(buy_time)
            sold_at = datetime.fromisoformat(sale_time)

            holding_seconds = int(
                (sold_at - bought_at).total_seconds()
            )

            hours, remainder = divmod(holding_seconds, 3600)
            minutes = remainder // 60

            holding_time = f"{hours}h {minutes}m"

            holding_hours = holding_seconds / 3600

            profit_per_hour = (
                net_profit / holding_hours
                if holding_hours > 0
                else 0
            )



        
    print(f"{asset_name} #{asset_id}")
    print(f"  Buy price: {buy_price:.8f} ETH")
    print(f"  Sale price: {sale_price:.8f} ETH")
    print(f"  Gross profit: {gross_profit:+.8f} ETH")
    print(f"  Gross ROI: {gross_roi:.2f}%")
    print(f"  Selling fee: {selling_fee:.8f} ETH")
    print(f"  Net proceeds: {net_proceeds:.8f} ETH")
    print(f"  Net profit: {net_profit:+.8f} ETH")
    print(f"  Net ROI: {net_roi:.2f}%")
    print(f"  Bought: {buy_time}")
    print(f"  Sold: {sale_time}")
    print(f"  Holding time: {holding_time}")
    print(
        f"  Net profit per hour: "
        f"{profit_per_hour:.10f} ETH"
    )
    print()


    conn.close()


if __name__ == "__main__":
    main()