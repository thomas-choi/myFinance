DELIMITER $$
CREATE PROCEDURE "sp_etf_trades"()
BEGIN
	declare maxdate date;
	set @maxdate = (SELECT max(Date) from Trading.`ETF_Options`);
	SELECT Date,Type, Trend, Symbol,Expiration,PnC,L_Strike,H_Strike,Entry,Target,Stop 
    from Trading.`ETF_Options` where date = @maxdate
    order by Trend, Type, Symbol, L_Strike;
END$$
DELIMITER ;
