library(shiny)
library(plotly)
navbarPage(
    title = 'Mutual Fund Analysis',
    tabPanel('NAV',
        fluidPage(
            sidebarPanel(
                selectizeInput("mf_name", "Select Mutual Fund:", choices=c())
            ),
            mainPanel(
                DT::dataTableOutput('table_nav')
            )
        )
    ),
    tabPanel('CAGR',
        fluidPage(
            h3('CAGR Table:'),
            DT::dataTableOutput('table_cagr'),
            h3('CAGR Summary Statistics:'),
            DT::dataTableOutput('table_cagr_desc'),
            h3('CAGR Frequency Analysis:'),
            plotlyOutput('plot_density'),
            h3('Histogram Analysis:'),
            selectInput("year_hist", "Year:", choices=c(1:10)),
            plotlyOutput('plot_hist'),
            h3('Rolling Returns Analysis:'),
            plotlyOutput('plot_rolling'),
            h3('NAV across Dates:'),
            checkboxInput('nav_log_y', 'Log Y-Axis', TRUE),
            plotlyOutput('plot_nav'),
            h3('Cumulative Return:'),
            dateInput('start_date', 'Plot From:', value='2015-01-01'),
            plotlyOutput('plot_cumr')
        )
    )

)