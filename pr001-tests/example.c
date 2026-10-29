int foo0(void) { return 0; }

#pragma overflowCheck
int foo1(void);
int global;
int foo2(void) { return 0; }
int foo3(void) { return 0; }

/* A later declaration must preserve foo2's recorded result. */
int foo2(void);
