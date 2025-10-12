/**
 * @name Simple test query
 * @description Find all print calls in Python code
 * @kind problem
 * @problem.severity info
 * @id py/test-print-calls
 */

import python

class PrintCall extends Call {
  PrintCall() {
    this.getFunc().(Name).getId() = "print"
  }
}

predicate isPrintCall(Call c) {
  c instanceof PrintCall
}

from PrintCall pc
select pc, "Print call found at line " + pc.getLocation().getStartLine().toString()