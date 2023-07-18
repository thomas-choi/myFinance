DELIMITER $$
CREATE PROCEDURE "sp_stock_trades"()
BEGIN
	declare maxdate date;
	set @maxdate = (SELECT max(Date) from Trading.`Stock_Options`);
	SELECT Date,Symbol,Expiration,PnC,Strike,Entry1,Entry2,Target,Stop from Trading.`Stock_Options` where date = @maxdate;
END$$
DELIMITER ;
