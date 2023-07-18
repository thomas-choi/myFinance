DELIMITER $$
CREATE PROCEDURE 'sp_stock_trades_V2'()
BEGIN
    DROP TEMPORARY TABLE if exists max_options_stock_tmp;
    create temporary table max_options_stock_tmp (
            maxdate	date,
            symbol	varchar(20),
            PRIMARY KEY (symbol)
    );
    insert into max_options_stock_tmp (SELECT max(Date), Symbol FROM Trading.Stock_Options group by symbol);
    SELECT * FROM max_options_stock_tmp t, Trading.Stock_Options s where t.maxdate=s.Date and t.symbol = s.Symbol order by s.Symbol;

END$$
DELIMITER ;
