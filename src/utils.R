get_cagr <- function(dt_navs, num_years=1){
    dt_navs[, prev_nav := shift(nav, 365*num_years)]
    dt_cagr <- na.omit(dt_navs)
    dt_cagr[, returns := nav/prev_nav - 1]
    dt_cagr[, cagr := (1 + returns) ^ (1/num_years) - 1]
    dt_cagr[, years := as.factor(num_years)]
    dt_cagr[, mean := mean(cagr, na.rm=TRUE)]
    dt_cagr[, median := median(cagr, na.rm=TRUE)]
    dt_cagr[, min := min(cagr, na.rm=TRUE)]
    dt_cagr[, max := max(cagr, na.rm=TRUE)]
    dt_cagr[, P25 := unlist(quantile(cagr, na.rm=TRUE)[2])]
    dt_cagr[, P75 := unlist(quantile(cagr, na.rm=TRUE)[4])]
    dt_cagr <- dt_cagr[, c('date', 'years', 'cagr', 'mean', 'median', 'min', 'max', 'P25', 'P75')]
    return (dt_cagr)
}

day_fn <- function(period){
    fn_list <- list("weekly" = wday, "monthly" = mday, "yearly" = yday)
    return (fn_list[[period]])
}

get_periodic_navs <- function(dt_navs, period='weekly', ord_num=1){
    dt_navs[, day := day_fn(period)(date)]
    dt_period_navs <- dt_navs[day == ord_num]
    dt_navs[, day := NULL]
    dt_period_navs[, day := NULL]
    dt_period_navs[, returns := nav / shift(nav) - 1]
    return(dt_period_navs)
}

# Rebasing based on a specific date
get_cumulative_returns <- function(dt_navs, from_date='2018-08-28'){
    dt_cumulative <- dt_navs[date >= from_date]
    dt_cumulative[, multiple := nav / shift(nav)]
    dt_cumulative$multiple[1] <- 1
    dt_cumulative[, cum_returns := cumprod(multiple)]
    return (dt_cumulative)
}

get_navs <- function(mf_url){
    # Directly using readLines on the URL
    json_data <- fromJSON(paste(readLines(mf_url), collapse=""))

    # MF Info
    dt_mf_info <- data.table(t(data.frame(unlist(json_data[[1]]))))

    # MF NAVs
    dt_navs <- data.table(do.call(rbind.data.frame, json_data[[2]]))
    dt_navs[, date := as.Date(date, format="%d-%m-%Y")]
    dt_navs[, nav := as.numeric(nav)]
    dt_navs <- dt_navs[order(date)]

    # Fill in for all dates
    all_dates <- seq.Date(min(dt_navs$date), max(dt_navs$date), by=1)
    dt_all_dates <- data.table(all_dates)
    names(dt_all_dates) <- 'date'
    dt_navs <- merge(dt_all_dates, dt_navs, by='date', all.x=TRUE)
    # Get the next observed value carried backward for missing days ("nocb")
    dt_navs$nav <- nafill(dt_navs$nav, type='nocb')
    return(dt_navs)
}
