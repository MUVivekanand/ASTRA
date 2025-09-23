package example

default allow = false

allow if {
    input.message == "hello"
}
