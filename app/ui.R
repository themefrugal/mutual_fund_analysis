library(shiny)
navbarPage(
    title = 'Mutual Fund Analysis',
    tabPanel('Tab 1',
        fluidPage(
            sidebarPanel(
                DT::dataTableOutput('table1')
            ),
            mainPanel(
                plotlyOutput('plot1')
            )
        )
    ),
    tabPanel('Tab 2',
        fluidPage(
            DT::dataTableOutput('table2')
        )
    )

)