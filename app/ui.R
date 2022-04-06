library(shiny)
library(plotly)
navbarPage(
    title = 'Mutual Fund Analysis',
    tabPanel('MF Analysis',
        fluidPage(
            sidebarPanel(
                selectizeInput("mf_name", "Select Mutual Fund:", choices=c())
            ),
            mainPanel(
                fluidPage(
                    h3('NAV:'),
                    fluidRow(column(6, DT::dataTableOutput('table_nav'))),
                    h3('NAV Charting:'),
                    checkboxInput('nav_log_y', 'Log Y-Axis', TRUE),
                    plotlyOutput('plot_nav'),
                    h3('CAGR:'),
                    fluidRow(column(6, DT::dataTableOutput('table_cagr'))),
                    h3('CAGR Summary:'),
                    DT::dataTableOutput('table_cagr_desc'),
                    h3('CAGR Frequency Analysis:'),
                    plotlyOutput('plot_density'),
                    h3('Histogram Analysis:'),
                    selectInput("year_hist", "Year:", choices=c(1:10)),
                    plotlyOutput('plot_hist'),
                    h3('Rolling Returns Analysis:'),
                    plotlyOutput('plot_rolling'),
                    h3('Cumulative Return:'),
                    fluidRow(
                        column(6, dateInput('start_date', 'Plot From:', value='2015-01-01')),
                        column(6, checkboxInput('cumr_log_y', 'Log Y-Axis', TRUE))
                    ),
                   selectizeInput("mf_name_cumr", "Add Fund:", choices=c(), multiple=TRUE),
                   plotlyOutput('plot_cumr'),
                   h3('Comparative Rolling Return:'),
                   selectizeInput("mf_name_comprr", "Add Fund:", choices=c(), multiple=TRUE),
                   selectInput("year_cagr", "Year:", choices=c(1:10)),
                   plotlyOutput('plot_comparative_roll')
                )

            )
        )
    )
)