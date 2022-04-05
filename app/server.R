source('./utils.R')
library(DT)
library(shiny)
library(rjson)
library(data.table)
library(ggplot2)
library(plotly)
library(dplyr)
library(memoise)

# Read from the internet, once in a while - may be once in a quarter or when necessary
# reading 'https://api.mfapi.in/mf' takes about 1 to 2 minutes
read_from_internet <- FALSE
if (read_from_internet){
    mf_list_url <- 'https://api.mfapi.in/mf'
    mf_list <- fromJSON(paste(readLines(mf_list_url), collapse=""))
    dt_mfs <- data.table(do.call(rbind.data.frame, mf_list))

    dt_mfs$schemeName <- sapply(dt_mfs$schemeName, first_upper)
    dt_mfs$schemeName <- sapply(dt_mfs$schemeName, prune_left)
    dt_mfs$schemeName <- sapply(dt_mfs$schemeName, remove_extra_space)
    dt_mfs <- dt_mfs[order(schemeName)]
    dt_mfs <- unique(dt_mfs)
    save(dt_mfs, file = './mf_codes.RData')
} else {
    load('./mf_codes.RData')
}

m_get_navs <- memoise(get_navs)
function(input, output, session) {
    updateSelectizeInput(session, "mf_name", choices = unique(dt_mfs$schemeName), server=TRUE)
    updateSelectizeInput(session, "mf_name_cumr", choices = unique(dt_mfs$schemeName), server=TRUE)
    updateSelectizeInput(session, "mf_name_comprr", choices = unique(dt_mfs$schemeName), server=TRUE)

    navs <- reactive({
        # Check this: There are multiple scheme codes for the same scheme name (in approx 20 instances)
        # As of now, we are taking the occurrence of first such instance
        scheme_code <- dt_mfs[schemeName == input$mf_name]$schemeCode[1]
        get_navs(scheme_code)
    })

    navs_1 <- reactive({
        # Check this: There are multiple scheme codes for the same scheme name (in approx 20 instances)
        # As of now, we are taking the occurrence of first such instance
        if (input$mf_name_comprr == ''){
            dt_navs <- data.table()
        } else {
            scheme_code <- dt_mfs[schemeName == input$mf_name_comprr]$schemeCode[1]
            dt_navs <- get_navs(scheme_code)
        }
        dt_navs
    })

    cagrs <- reactive({
        dt_cagrs <- rbindlist(lapply(c(1:10), function(x)get_cagr(navs(), x)))
    })

    cagrs_1 <- reactive({
        dt_cagrs <- rbindlist(lapply(c(1:10), function(x)get_cagr(navs_1(), x)))
    })

    cagr_desc <- reactive({
        dt_cagr_desc <- get_cagr_desc(cagrs())
    })

    output$table_nav <- DT::renderDataTable(
        datatable(navs(), filter='top', options = list(pageLength = 10)) %>%
            formatRound(columns=c('nav'), digits=3)
    )

    output$table_cagr <- DT::renderDataTable(
        datatable(cagrs(), filter='top', options = list(pageLength = 10)) %>%
            formatRound(columns=c('cagr'), digits=3)
    )

    output$table_cagr_desc <- DT::renderDataTable(
        datatable(cagr_desc(), filter='top', options = list(pageLength = 10)) %>%
            formatRound(columns=c('min', 'p25', 'mean', 'median', 'p75', 'max'), digits=3)
    )

    output$plot_density <- renderPlotly({
        p <- ggplot(cagrs(), aes(x=cagr, color=years)) + geom_density() +
            # scale_color_brewer(palette="RdYlBu") +
            theme_minimal()
        ggplotly(p)
    })

    output$plot_hist <- renderPlotly({
        dt_cagr_for_year <- cagr_desc()[years==input$year_hist]
        Mean <- dt_cagr_for_year$mean
        Median <- dt_cagr_for_year$median
        Min <- dt_cagr_for_year$min
        Max <- dt_cagr_for_year$max
        P25 <- dt_cagr_for_year$p25
        P75 <- dt_cagr_for_year$p75
        p <- ggplot(cagrs()[years == input$year_hist], aes(x=cagr)) +
            geom_histogram() +
            geom_vline(aes(xintercept = Mean), colour="black") +
            geom_vline(aes(xintercept = Median), colour="red") +
            geom_vline(aes(xintercept = Min), colour="black") +
            geom_vline(aes(xintercept = Max), colour="black") +
            geom_vline(aes(xintercept = P25), colour="blue") +
            geom_vline(aes(xintercept = P75), colour="blue")
        ggplotly(p)
    })

    output$plot_rolling <- renderPlotly({
        p <- ggplot(cagrs(), aes(x=date, y=cagr, color=years)) +
            geom_line()
        ggplotly(p)
    })

    # NAV Plot
    output$plot_nav <- renderPlotly({
        p <- ggplot(navs(), aes(x=date, y=nav)) + geom_line()
        if(input$nav_log_y){
            p <- p + scale_y_log10()
        }
        ggplotly(p)
    })

    # Cumulative Return Plot
    output$plot_cumr <- renderPlotly({
        dt_cumr <- get_cumulative_returns(navs(), input$start_date)
        dt_cumr[, 'scheme' := input$mf_name]

        list_cumr <- list()
        list_cumr <- c(list_cumr, list(dt_cumr))
        for (x in input$mf_name_cumr){
            scheme_code <- dt_mfs[schemeName == x]$schemeCode[1]
            dt_cumr <- get_cumulative_returns(m_get_navs(scheme_code), input$start_date)
            dt_cumr[, 'scheme' := x]
            list_cumr <- append(list_cumr, list(dt_cumr))
        }

        dt_cumr_all <- rbindlist(list_cumr)
        p <- ggplot(dt_cumr_all, aes(x=date, y=cum_returns, color=scheme)) + geom_line() + theme(legend.position = "bottom")
        if(input$cumr_log_y){
            p <- p + scale_y_log10()
        }
        ggplotly(p) %>% layout(legend = list(orientation = "h", y = -0.2))
    })

    # Comparative Rolling Return
    output$plot_comparative_roll <- renderPlotly({
        dt_cagr <- cagrs()
        dt_cagr[, scheme:= input$mf_name]

        dt_cagr_1 <- cagrs_1()
        dt_cagr_1[, scheme:= input$mf_name_comprr]
        dt_cagr <- rbindlist(list(dt_cagr, dt_cagr_1))

        p <- ggplot(dt_cagr[years == input$year_cagr], aes(x=date, y=cagr, color=scheme)) +
            geom_line()
        ggplotly(p) %>% layout(legend = list(orientation = "h", y = -0.2))
    })

}
# [years == input$year_rolling]