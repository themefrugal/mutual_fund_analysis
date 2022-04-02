source('../src/utils.R')
library(DT)
library(shiny)
library(rjson)
library(data.table)
library(ggplot2)
library(plotly)
library(dplyr)

# Read from the internet, once in a while - may be once in a quarter or when necessary
# reading 'https://api.mfapi.in/mf' takes about 1 to 2 minutes
read_from_internet <- FALSE
if (read_from_internet){
    mf_list_url <- 'https://api.mfapi.in/mf'
    mf_list <- fromJSON(paste(readLines(mf_list_url), collapse=""))
    dt_mfs <- data.table(do.call(rbind.data.frame, mf_list))
    save(dt_mfs, file = 'mf_codes.RData')
} else {
    load('./mf_codes.RData')
}

function(input, output, session) {
    updateSelectizeInput(session, "mf_name", choices = unique(dt_mfs$schemeName), server=TRUE)

    navs <- reactive({
        mf_url <- paste0('https://api.mfapi.in/mf/', dt_mfs[schemeName == input$mf_name]$schemeCode)
        dt_navs <- get_navs(mf_url)
        dt_navs
    })

    cagrs <- reactive({
        dt_cagrs <- rbindlist(lapply(c(1:10), function(x)get_cagr(navs(), x)))
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
        p <- ggplot(dt_cumr, aes(x=date, y=cum_returns)) + geom_line()
        if(input$cumr_log_y){
            p <- p + scale_y_log10()
        }
        ggplotly(p)
    })
}
# [years == input$year_rolling]