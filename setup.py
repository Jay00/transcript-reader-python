setup(
    ...
    scripts=['bin/funniest-joke'],
    ...
      entry_points = {
        'console_scripts': ['funniest-joke=funniest.command_line:main'],
    }
)