/**
 * @name SQL query built from user-controlled sources
 * @description Building a SQL query from user-controlled sources is vulnerable to insertion of
 *              malicious SQL code by the user.
 * @kind path-problem
 * @problem.severity error
 * @precision high
 * @id py/sql-injection
 * @tags security
 *       external/cwe/cwe-089
 */

import python
import semmle.python.security.dataflow.SqlInjectionQuery
import DataFlow::PathGraph

class SqlInjectionSink extends DataFlow::Node {
  SqlInjectionSink() {
    exists(Call call |
      call.getFunc().(Attribute).getName() = "execute" and
      this.asExpr() = call.getArg(0)
    )
  }
}

predicate isUserInput(DataFlow::Node source) {
  exists(Call call |
    call.getFunc().(Attribute).getName() = "request" and
    source.asExpr() = call
  )
}

from DataFlow::Node source, DataFlow::Node sink
where
  isUserInput(source) and
  sink instanceof SqlInjectionSink and
  DataFlow::flow(source, sink)
select sink, "This SQL query depends on user-provided input."